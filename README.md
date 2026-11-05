# Code Intelligence - DataBricks

A local web application that analyzes Databricks notebooks and supported source files, then generates three evidence-backed documents:

1. **Business understanding** — plain-language purpose, process, outcomes and risks.
2. **Developer documentation** — code structure, data flow, transformations, rules and dependencies.
3. **AI coding-agent guide** — invariants, risky areas, change constraints and regression checks.

The application itself is domain-agnostic.

## Features

- Upload `.py`, `.ipynb`, `.sql` and `.txt` source files.
- Parse Databricks Python cell separators (`# COMMAND ----------`) and Jupyter notebook cells.
- Select Gemini, OpenAI, Anthropic or Ollama and specify a model.
- Generate three audience-specific Markdown documents.
- Validate cited cell IDs and line ranges against the uploaded source.
- Local-first UI with cloud inference only through the provider selected by the user.
- Extension interfaces reserved for future LangGraph orchestration and LangSmith observability.

> Citation validation currently verifies that cited cell IDs and line ranges exist. It does not yet prove that the cited lines semantically entail the associated claim. Semantic claim-to-evidence verification is an important next enhancement.

## Quick start (Docker — recommended)

### Prerequisites

- Git
- Docker Desktop or Docker Engine with the Compose plugin
- An API key for the selected cloud provider, or a locally running Ollama instance

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd databricks-code-intelligence
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add the key for the provider you intend to use. For example:

```dotenv
GEMINI_API_KEY=your-key-here
```

Do not commit `.env`. It is excluded by `.gitignore`.

### 3. Start the application

```bash
docker compose up --build
```

### 4. Open the UI

Visit [http://localhost:8501](http://localhost:8501).

To stop the application, press `Ctrl+C`, or run:

```bash
docker compose down
```

## Run without Docker

Requires Python 3.11 or later.

```bash
python -m venv .venv
```

Activate the environment:

**macOS/Linux**
```bash
source .venv/bin/activate
```

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

Install and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Set the relevant provider environment variable before launching. For example:

**macOS/Linux**
```bash
export GEMINI_API_KEY="your-key-here"
```

**Windows PowerShell**
```powershell
$env:GEMINI_API_KEY="your-key-here"
```

## LLM provider configuration

| Provider | Environment variable | Default model shown in UI |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | `gemini-3.1-flash-lite` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Ollama | `OLLAMA_BASE_URL` (optional) | `llama3.2:3b` |

Model identifiers can be changed in the UI. Availability and access depend on the provider account and model.

### Ollama

Install and run Ollama on the host, then pull a model:

```bash
ollama pull llama3.2:3b
```

When using Docker Desktop, the default Ollama URL is `http://host.docker.internal:11434`. If Ollama runs elsewhere, set `OLLAMA_BASE_URL` in `.env`.

## How to use

1. Open the application.
2. Upload a supported source file.
3. Select the LLM provider and model in the sidebar.
4. Select **Analyze and generate documents**.
5. Review the three document tabs.
6. Review citation validation warnings.
7. Download each document as Markdown.
8. Use the source viewer to inspect the original cell code.

## Supported input formats and current limitations

- `.py`: Python source; Databricks `# COMMAND ----------` markers are treated as cell boundaries.
- `.ipynb`: Jupyter notebook cells are preserved.
- `.sql`: SQL source is treated as one cell.
- `.txt`: Plain text source is treated as one cell.

The initial parser is intentionally lightweight. It does not execute uploaded code. Scala, R, complex notebook export formats, `%run` dependency resolution and full Spark semantic analysis are not yet implemented. Python and SQL content are passed to the selected model for interpretation.

## Tests

```bash
pytest -q
```

## Architecture and design decisions

- **Streamlit** keeps the local UI simple and fast to run.
- **Parser/source representation** preserves cell boundaries so citations can point to original locations.
- **LLM provider adapter** keeps vendor-specific HTTP calls out of analysis and document-generation code.
- **Separate audience generators** ensure the same source is explained differently for managers, developers and coding agents.
- **Citation validator** checks that cited cells and line ranges exist in the uploaded source.
- **No notebook execution** is performed. Static analysis reduces the risk of executing untrusted uploaded code.

## Future enhancements

### LangChain
Add optional LangChain adapters for standardized chat-model integration, structured outputs, prompt management and retrieval. The current provider interface is the seam for this integration.

### LangGraph
Implement a graph-based workflow behind `AnalysisOrchestrator`, with nodes for parsing, structural analysis, business-rule extraction, data-flow analysis, document generation and citation validation. The initial application does not require LangGraph.

### LangSmith
Implement `ObservabilityProvider` using LangSmith tracing for run metadata, latency, token usage, model/prompt versions and failure diagnostics. Tracing should be opt-in and sensitive source content should be excluded or sanitized by default.

### Other next steps
- Semantic entailment checks between claims and cited source lines.
- Line-highlighted source viewer and clickable inline citations.
- Chunking and map/reduce analysis for large notebooks.
- Deeper Python AST, PySpark and SQL lineage analysis.
- Tests generated from extracted business rules and invariants.
- Export to PDF/HTML and downloadable source evidence bundle.
- Additional notebook languages and Databricks workspace import.

## Security notes

- Never commit API keys or `.env`.
- Cloud providers receive uploaded source code for inference when selected. Review organizational data-handling requirements before uploading sensitive code.
- Ollama can provide local inference, subject to local model/runtime setup.
- Uploaded code is not executed by this application.
- Future observability integrations should avoid capturing raw source code or secrets by default.

## Assignment sample

Place `cash_application_engine.py` in the repository's sample area or upload it directly through the UI. The generated documents for this sample should be committed under `generated/sample/` as part of the final assignment submission.
