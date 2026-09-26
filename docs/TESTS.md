# Tests

This page provides information on running tests on this application.

## Live integration tests

These make real API calls that may cost money, and the MCP server requires a
one-time OAuth authorization in your browser.

### Prerequisites

1. **Check `config.yaml`.** Confirm `llm.model_base_url`, `llm.model`, and
   `llm.api_key_env` point at the provider you intend to use, and that the base
   URL has no `/chat/completions` suffix (see [Configuration](../README.md#configuration)).
   A wrong model id fails on the first request with a 404 that looks a lot like
   a URL problem.

2. **Export the LLM API key**, using the variable name that `llm.api_key_env`
   names:

   ```bash
   # the variable named by llm.api_key_env -- currently NVIDIA_API_KEY
   export NVIDIA_API_KEY="nvapi-..."
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

### Run them in order

Each step isolates one moving part, so a failure tells you exactly what broke.
Run all commands from the project root.

| # | Command                                                                | Exercises                                  | LLM | MCP |
|---|------------------------------------------------------------------------|--------------------------------------------|-----|-----|
| 1 | `poetry run python tests/integration/test_openai_client.py`            | API key, base URL, model id                | ✅  | —   |
| 2 | `poetry run python tests/integration/test_calc_client.py`              | OAuth flow, MCP connection, tool discovery | —   | ✅  |
| 3 | `poetry run python tests/integration/test_llm.py`                      | Tool schemas accepted by the model         | ✅  | ✅  |
| 4 | `poetry run python tests/integration/test_llm_chat_completion_tool.py` | The Chat Completions agent loop            | ✅  | ✅  |
| 5 | `poetry run python tests/integration/test_llm_responses_tool.py`       | The Responses agent loop                   | ✅  | ✅  |
| 6 | `poetry run uvicorn math_ai_agent.app:app --reload`                    | The whole app end to end                   | ✅  | ✅  |

**Step 1 — LLM only.** Sends one question straight to the model, no MCP
involved. The `Connecting to <url> using model <model>` log line echoes exactly
what `config.yaml` supplied.

**Step 2 — MCP only.** The first run opens a browser for OAuth authorization;
the callback lands on port 10000. Tokens are cached encrypted under
`server.calculator_mcp.token_dir` (`~/.mathaiagent` by default), so later runs
skip the browser.

**Step 3 — LLM + tool discovery.** Discovers the calculator tools, sends
`4+4?` with the tool definitions attached, and logs the reply. It does *not*
dispatch tool calls — it confirms the model accepts the schemas.

**Step 4 — the full agent loop.** Multi-turn: the model requests a calculator
tool, the result is fed back, and the model answers. Look for
`Calling calculator MCP tool <name> with <args>` in the output. If the model
answers with no such lines, it is doing arithmetic in its head and the system
prompt is not taking effect.

**Step 5 — the Responses agent loop.** Same idea as step 4, but against the
Responses API (`POST /v1/responses`) rather than Chat Completions. It runs the
real `Agent`, so it exercises the code the app runs. Takes the question on the
command line, or prompts for it:

```bash
poetry run python tests/integration/test_llm_responses_tool.py "What is 4 + 4 * 3?"
```

Look for `function_call` items in the response and `Calling call_id: <id>,
tool_name: <name>` in the output. This step forces `llm.api_style` to
`responses`, so it always drives the Responses loop.

**Step 6 — the web app.** Open <http://127.0.0.1:8000>, type a math question,
and submit. `POST /prompt/` runs `Agent.run()`, which follows whichever path
`llm.api_style` selects.

### Verifying that config drives the client

Watch for this line, emitted whenever the client is built:

```
Initializing ChatCompletionClient with base_url=..., model=..., tool_count=N
```

(the class name is `ResponsesClient` when `llm.api_style` is `responses`)

Change `llm.model` in `config.yaml`, rerun step 4 or 5, and the line should
report the new value with no code change. `config.yaml` sets `DEBUG` for both
the `math_ai_agent` and `openai` loggers, so full request and response
bodies appear in the output.

### A note on `tests/integration/test_app.py`

```bash
poetry run uvicorn tests.integration.test_app:app --reload
```

This serves the same web UI but echoes your prompt straight back without calling
any LLM. Use it to check the page and the `POST /prompt/` wiring in isolation —
it does not exercise the agent.
