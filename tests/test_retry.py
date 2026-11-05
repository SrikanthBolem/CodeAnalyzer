import requests
from src.llm import factory


class FakeResponse:
    def __init__(self, status_code, headers=None, body=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error")


def google_429(retry_delay, daily=True):
    """Shape of Gemini's real quota error (trimmed)."""
    quota_id = "GenerateRequestsPerDayPerProjectPerModel-FreeTier" if daily else "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
    return FakeResponse(429, body={"error": {
        "code": 429,
        "message": "You exceeded your current quota, please check your plan and billing details.",
        "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": quota_id}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay},
        ]}})


def run(monkeypatch, outcomes):
    """Feed _post a scripted sequence of responses/exceptions; return (result, calls, sleeps)."""
    calls, sleeps = [], []
    seq = iter(outcomes)

    def fake_post(url, **kwargs):
        calls.append(url)
        item = next(seq)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(factory.requests, "post", fake_post)
    result = factory._post("http://x", sleep=sleeps.append, timeout=1)
    return result, calls, sleeps


def test_success_needs_no_retry(monkeypatch):
    r, calls, sleeps = run(monkeypatch, [FakeResponse(200)])
    assert r.status_code == 200 and len(calls) == 1 and sleeps == []


def test_retries_503_then_succeeds(monkeypatch):
    r, calls, sleeps = run(monkeypatch, [FakeResponse(503), FakeResponse(503), FakeResponse(200)])
    assert r.status_code == 200
    assert len(calls) == 3
    assert sleeps == [2, 4]


def test_gives_up_after_max_attempts(monkeypatch):
    r, calls, _ = run(monkeypatch, [FakeResponse(503)] * factory.MAX_ATTEMPTS)
    assert r.status_code == 503
    assert len(calls) == factory.MAX_ATTEMPTS


def test_honours_retry_after(monkeypatch):
    _, _, sleeps = run(monkeypatch, [FakeResponse(429, {"Retry-After": "7"}), FakeResponse(200)])
    assert sleeps == [7]


def test_client_errors_are_not_retried(monkeypatch):
    r, calls, _ = run(monkeypatch, [FakeResponse(404)])
    assert r.status_code == 404 and len(calls) == 1


def test_connection_error_is_retried(monkeypatch):
    r, calls, _ = run(monkeypatch, [requests.ConnectionError("down"), FakeResponse(200)])
    assert r.status_code == 200 and len(calls) == 2


def test_read_timeout_is_not_retried(monkeypatch):
    import pytest
    with pytest.raises(requests.ReadTimeout):
        run(monkeypatch, [requests.ReadTimeout("slow"), FakeResponse(200)])


def test_short_retry_info_delay_is_used(monkeypatch):
    r, calls, sleeps = run(monkeypatch, [google_429("12s", daily=False), FakeResponse(200)])
    assert r.status_code == 200 and sleeps == [12.0]


def test_long_retry_info_delay_fails_fast(monkeypatch):
    r, calls, sleeps = run(monkeypatch, [google_429("62164s")])
    assert r.status_code == 429
    assert len(calls) == 1 and sleeps == []


def test_daily_quota_message():
    import pytest
    with pytest.raises(RuntimeError) as exc:
        factory._check(google_429("62164s"), "Gemini", "gemini-3.5-flash")
    assert str(exc.value) == ("Gemini free-tier daily quota reached for model gemini-3.5-flash "
                              "(resets in about 17 h). Try another model or provider.")


def test_plain_rate_limit_message():
    import pytest
    with pytest.raises(RuntimeError) as exc:
        factory._check(FakeResponse(429, headers={"Retry-After": "20"}), "Anthropic", "m")
    assert "rate limit hit for model m (resets in about 20 s)" in str(exc.value)


def test_other_errors_still_raise_http_error():
    import pytest
    with pytest.raises(requests.HTTPError):
        factory._check(FakeResponse(404), "Gemini", "m")
