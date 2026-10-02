# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.0.17] - 2026-10-02

### Added

### Changed

- `build-verify` job name marks the SonarCloud scan as optional

### Fixed

- `build-verify` runs Sonar only when dispatched with `run-sonar` checked;
  it no longer runs on push

## [0.0.16] - 2026-10-02

### Added

### Changed

- `build-verify` no longer runs Sonar by default

### Fixed

## [0.0.15] - 2026-10-01

### Added

- `docs/SEQUENCE_DIAGRAM.md` and `docs/mcp_sequence.drawio` MCP client
  sequence diagram
- MCP Client Layers section in `docs/CLASS_DIAGRAM.md`
- Application startup and shutdown log messages

### Changed

- `CalcMCPClient` renamed to `CalcFastMCPClient`
- `CalcMCPConnection` renamed to `CalcFastMCPConnection`; its messages say
  connected/disconnected instead of open/closed
- GitHub workflows and jobs have descriptive display names
- `build-verify` runs on push; Sonar runs by default in it and `release`
- `release` no longer reinstalls dependencies after Poetry setup
- `release` builds and publishes through the shared `poetry-publish-pypi`
  workflow
- `cryptography` pinned to `50.0.2`

### Fixed

- Workflow inputs are passed to shell steps via `env` to prevent script
  injection
- Sonar analyzes `.github` and reports to `rubensgomes-org_math-ai-agent`
  instead of the shared `rubensgomes-org` key

## [0.0.14] - 2026-09-29

### Added

- `README.md` Links section with links to the `docs/` files

### Changed

- `README.md` badges: Python 3.14+, Poetry, Azure, and AI Assisted

### Fixed

## [0.0.13] - 2026-09-29

### Added

- `aca-destroy` workflow destroying the `mathagent` Azure Container App

### Changed

### Fixed

## [0.0.12] - 2026-09-29

### Added

- `Dockerfile`, `docker-compose.yml`, and `config/config_docker.yaml` for
  running in a container
- `aca-create` workflow provisioning the `mathagent` Azure Container App
- `build-deploy` workflow publishing the image and deploying it to ACA
- `CALCULATOR_MCP_URL` environment variable overriding
  `server.calculator_mcp.url`

### Changed

### Fixed

## [0.0.11] - 2026-09-28

### Added

### Changed

- README usage documents the health check and how to stop the app

### Fixed

## [0.0.10] - 2026-09-28

### Added

- `math-ai-agent --version` prints the installed version and exits

### Changed

- README simplified to PyPI installation, configuration, and usage; Git
  clone run instructions moved to `docs/DEVELOPMENT_SETUP.md`
- Build requires `poetry-core>=2.5`

### Fixed

## [0.0.9] - 2026-09-28

### Added

### Changed

- README documents running the PyPI package against the remote
  `calculator-mcp` on Prefect Horizon with GitHub OAuth
- App logs when the MCP connection opens and the agent is created
- `GET /` serves `index.html` as a file; the unused `/static` mount is
  removed

### Fixed

- Tool errors, such as division by zero, and invalid tool arguments are
  returned to the LLM as the tool output instead of failing the prompt
  with HTTP 500

## [0.0.8] - 2026-09-27

### Added

- `docs/NVIDIA-Nemotron-Open-Model-License-12-12-25.pdf`

### Changed

### Fixed

## [0.0.7] - 2026-09-27

### Added

### Changed

- Web page shows 6 rows in the Response box and no gap below the title
- Web page notes that Display Reasoning requires the Responses API
- Web page shows errors, including network and non-JSON responses, in
  red text below the form instead of in the Response box
- `llm.reasoning_summary` setting (`auto`, `concise`, or `detailed`)
  requests reasoning summaries; reasoning shows the summary when a
  reasoning item has no content
- `docs/CLASS_DIAGRAM.md` shows `0..1` multiplicity for
  `CalcMCPConnection._client`
- `docs/CLASS_DIAGRAM.md` shows the Chat Completions (March 2023) and
  Responses (March 2025) API release dates
- Config files link to the Nemotron 3 Super model card
- Token limits, content filters, and failed Responses API requests raise
  `TokenLimitError`, `ContentFilterError`, and `LLMRequestFailedError`;
  `POST /prompt/` returns 502, 422, and 502 for them, and logs any other
  error and returns 500
- Responses loop raises `ValueError` for `queued` and `in_progress`
  statuses instead of resending the request

### Fixed

## [0.0.6] - 2026-09-27

### Added

### Changed

- LLM request and response logs replace the tool definitions with a
  placeholder message

### Fixed

## [0.0.5] - 2026-09-27

### Added

- `llm.stateful` setting (default `false`); when `true`, the Responses
  loop stores responses and sends only new items with
  `previous_response_id`
- `llm.temperature` setting (0 to 2, set to 0.2); when unset, the provider
  default applies
- "Display Reasoning" Yes/No choice on the web page; `POST /prompt/`
  takes `display_reasoning` (default `true`) and, when `false`, returns
  only the final response

### Changed

- `prompt.py` renamed to `payload.py` and `Prompt` to `Payload`
- `to_openai_tools()` renamed to `to_chat_completions_tools()` in
  `CalcMCPClient` and `CalcMCPConnection`

### Fixed

## [0.0.4] - 2026-09-26

### Added

- `fastmcp.client` logger in `config_local.yaml` and `config_remote.yaml`
- Debug logs of the full context (instructions, history, tools) sent to
  the LLM on each call

### Changed

- With `llm.api_style: responses`, answers show `reasoning:` and
  `final response:` sections, collecting the reasoning from every turn
- `docs/PERFORMANCE.md` renamed to `docs/PYTHON_COROUTINE.md`

### Fixed

- uvicorn startup, shutdown, and access logs use the `config.yaml` log
  format instead of uvicorn's default

## [0.0.3] - 2026-09-26

### Added

- `llm.timeout_seconds` (default 120) and `llm.max_concurrent_prompts`
  (default 10) settings; prompts beyond the limit get HTTP 503
- Automatic reconnect and one retry when the calculator MCP connection
  drops during a tool call
- `flake8` dev dependency and `.flake8` config (80-character lines)
- `docs/PERFORMANCE.md` explaining the async event loop and shared clients

### Changed

- The app opens one calculator MCP connection and one LLM client at startup
  and reuses them for every prompt, instead of reconnecting per prompt and
  per tool call

### Fixed

- Web page shows the error message instead of `undefined` when a prompt
  request fails with an error response

## [0.0.2] - 2026-09-26

### Added

- `GET /health` endpoint returning 200 with plain text `OK`
- `math-ai-agent` command that starts the web app on the `web.host` and
  `web.port` set in `config.yaml` (default `127.0.0.1:9090`)

### Changed

### Fixed

## [0.0.1] - 2026-09-25

### Added

- Colored log level names in console output via `colorlog`; plain when
  stderr is not a terminal or `NO_COLOR` is set
- `uvicorn` logger in `config.yaml`, so server startup and error logs use the
  project's log format
- `build-verify` GitHub workflow (manual dispatch) running mypy, pylint,
  pip-audit, test coverage, and an optional SonarCloud quality gate
- `release` GitHub workflow (manual dispatch) that verifies, publishes to
  PyPI, creates a GitHub Release from `CHANGELOG.md`, and bumps the version
- `scripts/initvars.sh` resets the repository's GitHub Actions secrets
  (`PYPI_API_TOKEN`, `SONAR_TOKEN`) from the current shell environment
- Dependabot daily version updates for Poetry dependencies and GitHub
  Actions, grouping Python minor and patch updates into one pull request

### Changed

- The LLM system prompt moved from `_SYSTEM_INSTRUCTIONS` in `llm/agent.py`
  to the new `llm.system_instructions` setting in `config.yaml`
- `config.yaml` is parsed once into typed pydantic models by `get_config()`,
  replacing the `get_*()` and `is_oauth()` getters; an invalid
  `llm.api_style` now fails validation at startup
- `models.py` renamed to `prompt.py`
- Logging is configured once in `app.py` instead of on import of
  `config.py`, `llm/agent.py`, and `llm/client.py`

### Removed

- Unused `server.calculator_mcp.timeout` setting and `get_timeout()`
- `config.yaml` in the working directory is no longer loaded; set
  `MATHAIAGENT_CONFIG` to use a config other than the packaged default

### Fixed

- `pip-audit` failure on `diskcache` (PYSEC-2026-2447): OAuth tokens are
  stored in a `FileTreeStore` instead of a `DiskStore`, and the `diskcache`
  and `pathvalidate` test dependencies are removed. Existing tokens are not
  migrated, so the first run after upgrading repeats the OAuth login
- `CalcMCPClient` matches the current fastmcp API: `list_tools()` accepts
  `cache_mode`, and tools are read via `input_schema` instead of the
  deprecated `inputSchema`
- `scripts/test_github.sh` now parses GitHub's JSON correctly. The patterns
  assumed no whitespace after the colon (`"full_name":"..."`), but the API
  returns `"full_name": "..."`, so Test 3 printed an empty repository name,
  Test 7 printed `Rate limit: / remaining`, and Test 8 printed an empty tag
- `scripts/test_github.sh` follows redirects (`curl -sL`) when querying the
  API. A renamed or transferred repository returns HTTP 301, whose body has no
  `full_name` field, so Test 3 failed even though the repository was reachable
  via `git` and `gh` (both of which follow redirects transparently)
- `scripts/test_github.sh` fetches each API endpoint once instead of twice,
  halving its usage of the 60-per-hour unauthenticated rate limit
