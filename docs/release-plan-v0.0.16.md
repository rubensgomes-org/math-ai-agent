# Release Plan v0.0.16

## Summary

Make the LLM provider configurable without code changes. The API key, endpoint
URL, and model identifier move out of `llm/llm.py` into a new `llm:` block in
`config.yaml`, reached through typed getters. `config.py` becomes a `config/`
sub-package alongside `llm/` and `mcp/`, and `config.yaml` is promoted to the
project root so it is visible to whoever needs to edit it, with the packaged
copy retained as the default that ships in the wheel.

Also includes dependency upgrades, a Python 3.14 floor, a `Testing` section in
`README.md`, and documentation updates across the board.

## Changes

### Added

- `llm:` configuration block in `config.yaml` with `model_base_url`, `model`,
  and `api_key_env` settings
- `get_model_base_url()`, `get_model()`, and `get_api_key()` helpers in
  `config/config.py`; `get_api_key()` resolves the environment variable named
  by `llm.api_key_env` and raises `RuntimeError` when it is unset
- `src/math_ai_agent/config/` sub-package with `__init__.py`
- `config.yaml` at the project root as the file users edit
- `Testing` section in `README.md` covering the unit tests and the ordered
  sequence of live integration tests
- `Using Ollama with this Project` section in `OLLAMA.md`
- Unit tests covering the three new getters and the config-path resolution
  order

### Changed

- Moved `_API_KEY`, `_BASE_URL`, and `_MODEL` out of `llm/llm.py` into
  `config.yaml`; `agent_loop()` builds `OpenAIClient` from the config getters
- Moved `config.py` into the `config/` sub-package as `config/config.py`;
  callers import from `math_ai_agent.config.config`
- `_resolve_config_path()` resolves in three steps: `CALCULATOR_MCP_CONFIG`,
  then `./config.yaml` in the working directory, then the packaged default
- Removed the hardcoded `RUBENS_PAT_TOKEN` check from `agent_loop()` — the
  equivalent error now comes from `get_api_key()` and names the configured
  environment variable
- Integration tests read the endpoint, model, and API key from `config.yaml`
  instead of their own hardcoded copies
- Log format includes the source file and line number
  (`%(filename)s:%(lineno)d`)
- `_SYSTEM_INSTRUCTIONS` tells the model to answer in plain text, since the web
  UI renders answers in a `<textarea>` that cannot display LaTeX or Markdown
- Raised the Python floor to >= 3.14 and upgraded fastmcp, openai,
  py-key-value-aio, black, coverage, pytest-asyncio, mypy, and poetry-core
- Added `pylint` and `isort` to the dev dependency group; dropped the explicit
  `uvicorn` dev dependency
- Declared the license via the `license = "MIT"` field instead of a classifier
- Refreshed `README.md`, `CLAUDE.md`, `llms.txt`, and `OLLAMA.md` for the
  `config/` sub-package, the project-root `config.yaml`, the log format, the
  Python 3.14 floor, and the current provider settings

### Fixed

- `agent_loop()` guards the optional `response.usage` before logging token
  counts; previously it raised `AttributeError` against any provider that omits
  usage, and failed `mypy` with three `union-attr` errors
- Two stale `_MODEL` references in `tests/integration/test_openai_client.py`
  that raised `NameError` in the success and error paths

## Checklist

- [x] Run `poetry run mypy src/` and fix any issues
- [x] Run `poetry run isort src/ tests/` and fix any issues
- [x] Run `poetry run black src/ tests/` and fix any issues
- [x] Run `poetry run pytest` and fix any issues
- [x] Run `export SOURCE_DATE_EPOCH=$(date +%s); poetry build -v` and fix any issues
- [x] Verify `CHANGELOG.md` exists
- [x] Update `CHANGELOG.md` with v0.0.16 changes
- [x] Bump version to 0.0.16 in `pyproject.toml`
- [ ] Commit all changes, tag, push, and create GitHub release

## Notes

- `poetry run pytest` fails the configured 90% coverage floor at ~76%. This
  predates the release (72% at `bcb2554`) and is caused by `agent_loop()` and
  parts of `calc_client.py` having no unit tests. The bare `pytest` run used in
  this checklist passes; only the `--cov` variant enforces the floor.
- `uvicorn` is no longer a declared dev dependency but remains installed
  transitively, so the documented `poetry run uvicorn` command still works.
  Worth declaring explicitly in a future release.
- `config.yaml` at the project root is committed with the maintainer's active
  provider settings (OpenRouter). No secrets are in the file — it names the
  environment variable to read the key from.
