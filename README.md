# math-ai-agent

A small FastAPI web app that answers math questions by driving an LLM in a
tool-calling agent loop against a remote calculator MCP server configured in the
[config.yaml](config.yaml). The point of the
design is that the LLM is explicitly forbidden from doing arithmetic itself —
every operation must go through the MCP calculator tools.

## Features

- **FastAPI web UI** — simple form-based interface for submitting prompts
- **MCP client** — connects to a remote calculator MCP server via
  [FastMCP](https://github.com/jlowin/fastmcp), with optional OAuth
  authentication
- **Configurable** — MCP server URL, OAuth settings, LLM endpoint and model,
  timeouts, and logging are all driven by `config.yaml`; switching LLM providers
  needs no code change
- **Plain-text answers** — the model is instructed to reply without LaTeX or
  Markdown, since the web UI renders answers in a plain `<textarea>`

## Project Structure

```
config.yaml             # Active configuration -- edit this one
src/math_ai_agent/
  app.py                # FastAPI application (web UI + /prompt endpoint)
  models.py             # Pydantic models (Prompt) for request validation
  config/
    config.py           # Configuration helpers (loads config.yaml, logging)
    config.yaml         # Packaged default, used when no other is found
  llm/
    llm.py              # OpenAI client wrapper and agent loop
  mcp/
    calc_client.py      # Calculator MCP client and helper functions
  static/
    index.html          # Web UI served at /
tests/
  integration/
    test_calc_client.py      # Integration test for the MCP client
    test_openai_client.py    # Integration test for the raw OpenAI SDK
    test_llm.py              # Integration test for the OpenAIClient wrapper
    test_llm_tool.py         # Integration test for LLM with tool calling
    test_app.py              # FastAPI integration test application
    app_text.txt             # Sample text fixture for integration tests
  test_calc_client.py        # Unit tests for calc_client.py
  test_config.py             # Unit tests for config/config.py
  test_llm.py                # Unit tests for llm.py
  test_app.py                # Unit tests for app.py
```

## Configuration

All settings live in `config.yaml` at the project root:

- **`server.calculator_mcp.url`** — MCP server endpoint
- **`server.calculator_mcp.is_oauth`** — enable/disable OAuth authentication
- **`server.calculator_mcp.token_dir`** — directory for storing OAuth tokens
- **`server.calculator_mcp.callback_port`** — fixed port for the OAuth callback
- **`server.calculator_mcp.timeout`** — HTTP client timeout in seconds
- **`llm.model_base_url`** — base URL of the LLM model inference endpoint
- **`llm.model`** — LLM model identifier
- **`llm.api_key_env`** — *name* of the environment variable holding the LLM API
  key (currently `OPENROUTER_API_KEY`)
- **`logging`** — Python `logging.config.dictConfig` block. The `standard`
  formatter includes the source file and line number
  (`%(filename)s:%(lineno)d`), so log lines point at the code that emitted
  them

The file is located in this order, first match wins:

1. The path in the `CALCULATOR_MCP_CONFIG` environment variable, if set.
2. `config.yaml` in the current working directory — the copy at the project
   root, which is what you edit when running from a clone.
3. `src/math_ai_agent/config/config.yaml` — the default bundled into the
   package, used by `pip`-installed copies.

Because of step 2, run the app from the project root so your edits take effect.

When OAuth is enabled, set `OAUTH_STORAGE_ENCRYPTION_KEY` to a
Fernet-compatible key.

The LLM API key itself is never stored in `config.yaml` — the file only names
the environment variable to read it from, so set that variable (whatever
`llm.api_key_env` points at) before starting the server.

`llm.model_base_url` must be the API **base** URL, not a full route: the SDK
appends `/chat/completions` itself. Use `https://api.openai.com/v1`, not
`https://api.openai.com/v1/chat/completions` — a full route produces requests to
`.../chat/completions/chat/completions` and a 404.

Switching providers is a config-only change. For example:

| Provider             | `model_base_url`             | `model`                      | `api_key_env`                 |
|----------------------|------------------------------|------------------------------|-------------------------------|
| OpenRouter           | `https://openrouter.ai/api/v1` | any slug from their catalog | `OPENROUTER_API_KEY`          |
| OpenAI               | `https://api.openai.com/v1`  | `gpt-5.6`                    | `OPENAI_API_KEY`              |
| Ollama (local, free) | `http://localhost:11434/v1`  | `phi`                        | any variable set to any value |

Any OpenAI-compatible endpoint works, since the app talks to it through the
OpenAI SDK's Chat Completions API.

See [OLLAMA.md](OLLAMA.md) for running models locally.

## Setup

See [SETUP.md](SETUP.md) for detailed instructions on setting up the development
environment (pyenv, poetry, virtual environment, PyCharm, etc.).

### Quick Start

```bash
# Clone and install
git clone https://github.com/rubensgomes/math-ai-agent
cd math-ai-agent
poetry install

# Run the FastAPI server
poetry run uvicorn math_ai_agent.app:app --reload

# Change to the project root folder
cd $(git rev-parse --show-toplevel) || exit
# Run the MCP integration test client
poetry run python tests/integration/test_calc_client.py
# Run the FastAPI web server test
poetry run uvicorn tests.integration.test_app:app --reload
```

The integration commands above need credentials and an OAuth authorization —
see [Testing](#testing) for the prerequisites and the full sequence.

## Testing

There are two kinds of tests in this project:

- **Unit tests** (`tests/*.py`) — fast, fully mocked, no network. This is what
  `pytest` collects.
- **Live integration tests** (`tests/integration/*.py`) — standalone scripts
  that call the real LLM and the real MCP server. They contain no
  `test_`-prefixed functions, so **`pytest` does not collect them**; they only
  run as the scripts shown below.

### Unit tests

```bash
poetry run pytest

# With coverage (branch coverage, minimum 90%)
poetry run pytest --cov=src/ --cov-report=term-missing
```

No credentials or network access required.

### Live integration tests

These make real API calls that may cost money, and the MCP server requires a
one-time OAuth authorization in your browser.

#### Prerequisites

1. **Check `config.yaml`.** Confirm `llm.model_base_url`, `llm.model`, and
   `llm.api_key_env` point at the provider you intend to use, and that the base
   URL has no `/chat/completions` suffix (see [Configuration](#configuration)).
   A wrong model id fails on the first request with a 404 that looks a lot like
   a URL problem.

2. **Export the LLM API key**, using the variable name that `llm.api_key_env`
   names:

   ```bash
   # the variable named by llm.api_key_env -- currently OPENROUTER_API_KEY
   export OPENROUTER_API_KEY="..."
   ```

3. **Export an OAuth storage key.** Generate a Fernet key once and reuse it —
   changing it makes previously cached tokens unreadable and forces a
   re-authorization:

   ```bash
   # Generate a key (do this once, then save it)
   poetry run python -c \
     'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

   export OAUTH_STORAGE_ENCRYPTION_KEY="<the generated key>"
   ```

   This is required whenever `server.calculator_mcp.is_oauth` is `true`. It is
   read directly from the environment, so a missing value raises a bare
   `KeyError`.

4. **Free port 10000** for the OAuth callback
   (`server.calculator_mcp.callback_port`).

#### Run them in order

Each step isolates one moving part, so a failure tells you exactly what broke.
Run all commands from the project root.

| # | Command                                                     | Exercises                                  | LLM | MCP |
|---|-------------------------------------------------------------|--------------------------------------------|-----|-----|
| 1 | `poetry run python tests/integration/test_openai_client.py` | API key, base URL, model id                | ✅  | —   |
| 2 | `poetry run python tests/integration/test_calc_client.py`   | OAuth flow, MCP connection, tool discovery | —   | ✅  |
| 3 | `poetry run python tests/integration/test_llm.py`           | Tool schemas accepted by the model         | ✅  | ✅  |
| 4 | `poetry run python tests/integration/test_llm_tool.py`      | The full agent loop with tool dispatch     | ✅  | ✅  |
| 5 | `poetry run uvicorn math_ai_agent.app:app --reload`         | The whole app end to end                   | ✅  | ✅  |

**Step 1 — LLM only.** Sends one question straight to the model, no MCP
involved. The `Connecting to <url> using model <model>` log line echoes exactly
what `config.yaml` supplied.

**Step 2 — MCP only.** The first run opens a browser for OAuth authorization;
the callback lands on port 10000. Tokens are cached encrypted under
`server.calculator_mcp.token_dir` (`/tmp/.fastmcp/oauth-tokens` by default), so
later runs skip the browser. Because `/tmp` is cleared on reboot, an unexpected
re-authorization prompt usually means exactly that.

**Step 3 — LLM + tool discovery.** Discovers the calculator tools, sends
`4+4?` with the tool definitions attached, and logs the reply. It does *not*
dispatch tool calls — it confirms the model accepts the schemas.

**Step 4 — the full agent loop.** Multi-turn: the model requests a calculator
tool, the result is fed back, and the model answers. Look for
`Calling calculator MCP tool <name> with <args>` in the output. If the model
answers with no such lines, it is doing arithmetic in its head and the system
prompt is not taking effect.

**Step 5 — the web app.** Open <http://127.0.0.1:8000>, type a math question,
and submit. `POST /prompt/` runs the same `agent_loop()` exercised in step 4.

#### Verifying that config drives the client

Watch for this line, emitted whenever the client is built:

```
Initializing OpenAIClient with base_url=..., model=..., tool_count=N
```

Change `llm.model` in `config.yaml`, rerun step 4, and the line should report
the new value with no code change. `config.yaml` sets `DEBUG` for both the
`math_ai_agent` and `openai` loggers, so full request and response bodies appear
in the output.

#### A note on `tests/integration/test_app.py`

```bash
poetry run uvicorn tests.integration.test_app:app --reload
```

This serves the same web UI but echoes your prompt straight back without calling
any LLM. Use it to check the page and the `POST /prompt/` wiring in isolation —
it does not exercise the agent.

## License

See the disclaimer headers in each source file for copyright and warranty
information.
