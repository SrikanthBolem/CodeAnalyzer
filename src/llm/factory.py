import os
import time
import requests
from .base import LLMProvider

# Transient statuses worth retrying: rate limit, server errors, and overload (529 is Anthropic's).
RETRY_STATUSES = {429, 500, 502, 503, 504, 529}
MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 30

def _error_body(r):
    try:
        body = r.json()
    except Exception:
        return {}
    err = body.get("error") if isinstance(body, dict) else None
    return err if isinstance(err, dict) else {}

def _retry_delay(r):
    """Seconds the provider asks us to wait: Retry-After header, else Google's RetryInfo detail."""
    retry_after = r.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return float(retry_after)
    for detail in _error_body(r).get("details", []) or []:
        if isinstance(detail, dict) and detail.get("@type", "").endswith("RetryInfo"):
            try:
                return float(str(detail.get("retryDelay", "")).rstrip("s"))
            except ValueError:
                return None
    return None

def _post(url, sleep=time.sleep, **kwargs):
    """POST with exponential backoff on transient HTTP errors and dropped connections.

    Timeouts are not retried: a slow model would otherwise multiply the wait.
    If the provider asks for a wait longer than MAX_DELAY_SECONDS (e.g. a daily quota),
    the response is returned at once rather than retried pointlessly.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = requests.post(url, **kwargs)
        except requests.ConnectionError:
            if attempt == MAX_ATTEMPTS:
                raise
        else:
            if r.status_code not in RETRY_STATUSES or attempt == MAX_ATTEMPTS:
                return r
            delay = _retry_delay(r)
            if delay is not None:
                if delay > MAX_DELAY_SECONDS:
                    return r
                sleep(delay)
                continue
        sleep(min(BASE_DELAY_SECONDS * 2 ** (attempt - 1), MAX_DELAY_SECONDS))

def _format_wait(seconds):
    if seconds >= 3600:
        return f"about {round(seconds / 3600)} h"
    if seconds >= 60:
        return f"about {round(seconds / 60)} min"
    return f"about {round(seconds)} s"

def _check(r, provider, model):
    """Raise a readable error for quota/rate limits; otherwise defer to raise_for_status."""
    if r.status_code == 429:
        err = _error_body(r)
        quota_ids = [v.get("quotaId", "") for d in err.get("details", []) or [] if isinstance(d, dict)
                     for v in d.get("violations", []) or [] if isinstance(v, dict)]
        text = (err.get("message", "") + " " + " ".join(quota_ids)).lower()
        delay = _retry_delay(r)
        when = f" (resets in {_format_wait(delay)})" if delay else ""
        if "quota" in text:
            tier = "free-tier " if "free" in text else ""
            period = "daily " if "perday" in text else ""
            raise RuntimeError(f"{provider} {tier}{period}quota reached for model {model}{when}. "
                               "Try another model or provider.")
        raise RuntimeError(f"{provider} rate limit hit for model {model}{when}. "
                           "Wait a moment and try again, or switch model or provider.")
    r.raise_for_status()

PROVIDERS = {
    "Gemini": {"default_model": "gemini-3.1-flash-lite", "hint": "Set GEMINI_API_KEY."},
    "OpenAI": {"default_model": "gpt-4.1-mini", "hint": "Set OPENAI_API_KEY."},
    "Anthropic": {"default_model": "claude-sonnet-4-20250514", "hint": "Set ANTHROPIC_API_KEY."},
    "Ollama": {"default_model": "llama3.2:3b", "hint": "Run Ollama locally and pull the selected model."},
}

class HTTPProvider(LLMProvider):
    def __init__(self, name, model):
        self.name, self.model = name, model

    def generate(self, prompt, system=""):
        if self.name == "Gemini":
            key = os.getenv("GEMINI_API_KEY")
            if not key: raise RuntimeError("GEMINI_API_KEY is not set.")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            headers = {"x-goog-api-key": key}
            payload = {"systemInstruction":{"parts":[{"text":system}]},"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.1}}
            r = _post(url, headers=headers, json=payload, timeout=180)
            _check(r, self.name, self.model)
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]

        if self.name == "OpenAI":
            key = os.getenv("OPENAI_API_KEY")
            if not key: raise RuntimeError("OPENAI_API_KEY is not set.")
            headers = {"Authorization":f"Bearer {key}"}
            payload = {"model":self.model,"input":[{"role":"system","content":system},{"role":"user","content":prompt}]}
            r = _post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=180)
            _check(r, self.name, self.model)
            data = r.json()
            return "".join(x.get("text","") for item in data.get("output",[]) for x in item.get("content",[]) if x.get("type")=="output_text")

        if self.name == "Anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key: raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            headers = {"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"}
            payload = {"model":self.model,"max_tokens":6000,"system":system,"messages":[{"role":"user","content":prompt}]}
            r = _post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=180)
            _check(r, self.name, self.model)
            return "\n".join(x.get("text","") for x in r.json().get("content",[]) if x.get("type")=="text")

        if self.name == "Ollama":
            base = os.getenv("OLLAMA_BASE_URL","http://host.docker.internal:11434")
            payload = {"model":self.model,"stream":False,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}]}
            r = _post(f"{base.rstrip('/')}/api/chat", json=payload, timeout=600)
            _check(r, self.name, self.model)
            return r.json()["message"]["content"]
        raise ValueError(f"Unsupported provider: {self.name}")

def build_provider(name, model):
    if name not in PROVIDERS: raise ValueError(f"Unsupported provider: {name}")
    return HTTPProvider(name, model)
