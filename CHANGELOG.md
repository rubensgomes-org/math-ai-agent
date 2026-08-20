# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.16] - 2026-08-20

### Added

- `llm:` configuration block in `config.yaml` with `model_base_url`,
  `model`, and `api_key_env` settings
- `get_model_base_url()`, `get_model()`, and `get_api_key()` helpers in
  `config/config.py`; `get_api_key()` resolves the environment variable named by
  `llm.api_key_env` and raises `RuntimeError` when it is unset
- Unit tests in `tests/test_config.py` covering the three new getters and the
  config-path resolution order

### Changed

- Moved `_API_KEY`, `_BASE_URL`, and `_MODEL` out of `llm/llm.py` into
  `config.yaml`; `agent_loop()` now builds `OpenAIClient` from the config
  getters
- Removed the hardcoded `RUBENS_PAT_TOKEN` check from `agent_loop()` — the
  equivalent error now comes from `get_api_key()` and names the configured
  environment variable
- Integration tests (`test_llm.py`, `test_llm_tool.py`, `test_openai_client.py`)
  read the endpoint, model, and API key from `config.yaml` instead of their own
  hardcoded copies
- Documented the `llm:` settings in `README.md`, `CLAUDE.md`, and `llms.txt`
- Added a "Using Ollama with this Project" section to `OLLAMA.md` covering the
  `llm:` config block and the tool-calling requirement
- Refreshed `README.md`, `CLAUDE.md`, and `llms.txt` for the `config/`
  sub-package, the project-root `config.yaml`, the log format, and the current
  provider settings
- Log format now includes the source file and line number
  (`%(filename)s:%(lineno)d`)
- `_SYSTEM_INSTRUCTIONS` now tells the model to answer in plain text, since the
  web UI renders the answer in a `<textarea>` that cannot display LaTeX or
  Markdown
- Moved `config.py` into a new `src/math_ai_agent/config/` sub-package as
  `config/config.py`, alongside `llm/` and `mcp/`; callers now import from
  `math_ai_agent.config.config`
- `config.yaml` is now visible at the project root; a copy remains inside the
  package as the default that ships in the wheel
- `_resolve_config_path()` resolves in three steps: `CALCULATOR_MCP_CONFIG`,
  then `./config.yaml` in the working directory, then the packaged default
- Raised the Python floor to `>=3.14` and upgraded fastmcp, openai,
  py-key-value-aio, black, coverage, pytest-asyncio, mypy, and poetry-core
- Added `pylint` and `isort` to the dev dependency group; dropped the explicit
  `uvicorn` dev dependency
- Declared the license via the `license = "MIT"` field instead of the
  `License :: OSI Approved :: MIT License` classifier
- Added a `Testing` section to `README.md` covering the unit tests and the
  ordered sequence of live integration tests, with prerequisites, per-step
  explanations, and a provider-switching table

### Fixed

- `agent_loop()` guards the optional `response.usage` before logging token
  counts; previously it raised `AttributeError` against any provider that omits
  usage
- Two stale `_MODEL` references in `tests/integration/test_openai_client.py`
  that raised `NameError` in the success and error paths

## [0.0.15] - 2026-04-04

### Changed

- Fixed stale integration test command in `CLAUDE.md` (`test_calc_mcp_client.py`
  → `test_calc_client.py`)
- Updated project structure in `README.md` to show `llm/` and `mcp/`
  sub-packages and renamed test files
- Updated architecture description and project structure in `llms.txt` to
  reflect four-component design with `llm/` and `mcp/` sub-packages
- Updated `TODO.md` to reference `llm/llm.py` instead of `app.py`, removed
  completed modularization item
- Added documentation review step to `.claude/commands/release-plan.md`

## [0.0.14] - 2026-04-04

### Added

- `src/math_ai_agent/mcp/` sub-package with `__init__.py`
- `src/math_ai_agent/llm/` sub-package with `__init__.py`

### Changed

- Moved `calc_mcp_client.py` into `mcp/` sub-package and renamed to `calc_client.py`
- Moved `llm.py` into `llm/` sub-package
- Moved `get_mcp_tools()` and `call_tool()` from `app.py` to `mcp/calc_client.py`
- Moved `agent_loop()` and LLM configuration constants from `app.py` to `llm/llm.py`
- Updated module docstrings in `llm/llm.py` and `mcp/calc_client.py` to reflect new contents
- Fixed `CalcMCPClient.list_tools()` signature to match superclass (`max_pages` parameter)
- Renamed `tests/test_calc_mcp_client.py` to `tests/test_calc_client.py`
- Renamed `tests/integration/test_calc_mcp_client.py` to `tests/integration/test_calc_client.py`
- Updated all imports across source and test files for new module paths
- Simplified `app.py` to only contain FastAPI routes, delegating to `llm` and `mcp` sub-packages

## [0.0.13] - 2026-04-03

### Changed

- Renamed `main.py` to `app.py` (FastAPI application module)
- Renamed `tests/test_main.py` to `tests/test_app.py`
- Renamed `tests/integration/app.py` to `tests/integration/test_app.py`
- Refactored `get_mcp_tools()` to use `async with` context manager, fixing resource leak from manual `__aenter__()` call
- Changed `_SYSTEM_INSTRUCTIONS` from triple-quoted string to implicit concatenation, removing leading newline
- Updated all docstrings in `app.py` to follow Google Python Style Guide (added `Args`, `Returns`, `Raises` sections)
- Improved `get_mcp_tools()` return type from `list[dict]` to `list[dict[str, object]]`
- Fixed `agent_loop` return type annotation from `None` to `str`
- Fixed `None` finish_reason case to `continue` instead of falling through
- Replaced f-string logging with `%s` lazy formatting
- Updated `CLAUDE.md`, `README.md`, `llms.txt` with renamed file references
- Updated `TODO.md` with completed docstring review item
- Updated `test_prompt_returns_answer` and `test_prompt_strips_whitespace` to mock `agent_loop`
- Added `_API_KEY` validation with `RuntimeError` in `agent_loop`
- Added mypy type fixes (`list[Any]` context, `assert tool_calls`, `type: ignore` for union-attr)

### Removed

- Removed `get_calcmcp_client()` helper (leaked async context manager)
- Removed commented-out `_MODEL = "openai/gpt-5"` dead code
- Removed redundant MCP connection/discovery in `/prompt/` endpoint
- Removed stale numbered step comments in `/prompt/` handler

## [0.0.12] - 2026-03-21

### Added

- `tests/integration/app.py` FastAPI integration test application
- `tests/integration/app_text.txt` sample text fixture for integration tests
- `uvicorn` dev dependency for running integration test server
- Module docstring workflow description in `main.py`

### Changed

- Renamed `MathQuestion` model to `Prompt` with field `question` → `text`
- Updated `POST /prompt/` endpoint and frontend JS to use `Prompt.text`
- Updated `<noscript>` block and button formatting in `index.html`
- Bumped `fastmcp` 3.1.0 → 3.1.1
- Bumped `openai` 2.26.0 → 2.29.0
- Bumped `black` 26.3.0 → 26.3.1
- Bumped `coverage` 7.13.4 → 7.13.5
- Bumped `pytest-cov` 7.0.0 → 7.1.0
- Updated project structure in `README.md` and `llms.txt` with new integration test files

### Fixed

- Fixed `test_main.py`: two tests still sending `{"question": ...}` instead of `{"text": ...}` after model rename

## [0.0.11] - 2026-03-15

### Changed

- Refactored `OpenAIClient` from singleton with class variables to a regular instance-based class
- Renamed `OpenAIClient.__init__` parameters: removed leading underscores (`_api_key` → `api_key`, `_base_url` → `base_url`, `_model` → `model`, `_calcmcp_tools` → `calcmcp_tools`)
- Changed `create_response` from `@staticmethod` back to instance method
- Replaced piecemeal response logging in `create_response` with full JSON dump via `response.model_dump()`
- Formatted tool definitions debug log as indented JSON for readability
- Renamed `memory` variable to `messages` in integration tests for consistency
- Refactored agent loop in `test_llm_tool.py` to use `match`/`case` on `finish_reason`
- Updated docstrings in `llm.py`, `test_llm.py`, `test_llm_tool.py`
- Updated project structure in `README.md` and `llms.txt` with missing `test_llm.py` unit test
- Fixed isort version `0.0.1+` → `8.0.1+` in `SETUP.md`

### Fixed

- Fixed `test_llm_tool.py`: infinite `while message.tool_calls` loop replaced with `for` loop
- Fixed `test_llm_tool.py`: typo "propertly" → "properly"
- Fixed `test_llm.py`: typo "mathe" → "math" in system instructions
- Fixed trailing whitespace in system instructions
- Removed unused `patch` import from `tests/test_llm.py`
- Removed duplicate and redundant log statements across integration tests

## [0.0.10] - 2026-03-15

### Added

- `tests/integration/test_llm_tool.py` integration test for LLM tool calling with interactive agent loop
- `tests/test_llm.py` unit tests for `OpenAIClient` (12 tests, 100% coverage on `llm.py`)
- `tests` and `__main__` logger entries in `config.yaml` for test log visibility
- Module docstring in `models.py`
- Return type annotation and Args/Returns docstrings in `main.py` functions
- Args/Returns docstrings in `test_llm_tool.py` functions

### Fixed

- Fixed `test_llm_tool.py`: wrong attribute `tool_call.tool_name` to `tool_call.function.name`
- Fixed `test_llm_tool.py`: missing `await` on `call_tool()` async function
- Fixed `test_llm_tool.py`: duplicate assistant message appended to memory
- Fixed `test_llm_tool.py`: agent loop now handles multiple tool calls and multi-round tool calling
- Fixed `test_llm_tool.py`: assistant message with `tool_calls` preserved (not stripped to plain content)
- Updated stale `llm.py` description in `llms.txt`
- Updated stale `litellm` dependency to `openai` in `llms.txt`
- Added missing `models.py`, `test_llm.py`, `test_llm_tool.py` to project structure in `README.md` and `llms.txt`
- Fixed Python version `3.14.2` to `3.14.3` in `SETUP.md`
- Aligned `gh` CLI version prerequisite in `RELEASE.md` to match `SETUP.md`

## [0.0.9] - 2026-03-14

### Changed

- Refactored `OpenAIClient` in `llm.py` to accept `_api_key`, `_base_url`, `_model`, and `_calcmcp_tools` as constructor parameters (removed module-level constants)
- Replaced synchronous `OpenAI` client with `AsyncOpenAI` for proper async support
- Updated module and class docstrings in `llm.py` to reflect current architecture
- Updated `README.md` project structure with `models.py`, `test_llm.py`, and corrected `llm.py` description

### Added

- `tests/integration/test_llm.py` integration test for the `OpenAIClient` wrapper
- Input validation in `OpenAIClient.__init__` for all constructor parameters
- Singleton guard to ensure `OpenAIClient` class variables are initialized only once
- Comprehensive logging across all functions in `src/` modules
- Logging in `tests/integration/test_openai_client.py` with timing and model/API type display
- Try/except error handling in `tests/integration/test_openai_client.py`
- Docstrings to all classes and functions in `src/` modules
- Guard for `None` content in `create_response` when LLM returns tool calls
- Debug logging of all message attributes in `create_response`

### Fixed

- Fixed `OpenAIClient.__init__` assigning to local variables instead of class variables
- Fixed circular dependency in `config.py` where `logger.debug` was called before logger was initialized
- Fixed `test_llm.py`: corrected method name, fixed nested dict, added `asyncio.run()`, proper context manager usage
- Removed unused imports from `llm.py` and `test_llm.py`

## [0.0.8] - 2026-03-09

### Changed

- Renamed `tests/integration/openai_client.py` to `test_openai_client.py` (pytest discovery convention)

### Fixed

- Fixed `chat.completions` response handling: replaced invalid `response.output_text` with `response.choices[0].message.content`
- Updated docstring run command to reference renamed filename
- Updated README.md, CHANGELOG.md, and llms.txt with renamed filename

## [0.0.7] - 2026-03-08

### Changed

- Refactored `CalcMCPClient` to extend `fastmcp.Client` directly (removed wrapper delegation pattern)
- Renamed `CalcMCP` class to `CalcMCPClient`
- Renamed `mcp_calc.py` to `calc_mcp_client.py` (PEP 8 module naming)
- Renamed integration test to `test_calc_mcp_client.py` (pytest discovery convention)
- Changed `to_openai_tools()` from static method to async instance method
- Integration test now prints tools in OpenAI function-calling JSON format
- Callers use inherited `call_tool()` instead of removed `call()` wrapper

### Removed

- Removed unit tests for integration test source code
- Removed dead `create_client()` function and unused imports from integration test

### Fixed

- Fixed stale log message referencing old `CalcMCP.tools` attribute name
- Fixed stale docstrings and documentation with current file names and architecture
- Updated README.md, CLAUDE.md, and llms.txt to reflect current project structure

## [0.0.6] - 2026-03-07

### Added

- `OLLAMA.md` documentation for installing and running Ollama with local LLM models
- `llm.py` module with system instructions for the math tutor LLM
- `openai` DEBUG-level logger in `config.yaml` for OpenAI SDK request/response tracing
- Logging integration in `tests/integration/test_openai_client.py` using project config

### Changed

- Renamed `OLLAMAmd` to `OLLAMA.md` (proper Markdown extension)
- Fixed typo in `OLLAMA.md`: "Linus" to "Linux"

## [0.0.5] - 2026-03-06

### Added

- `CalcMCP` async context manager class (`mcp_calc.py`) wrapping the calculator MCP server with tool caching and `call()` API
- Unit tests for `mcp_calc.py` (11 tests, 100% coverage)
- `tests/integration/` directory for integration test scripts
- Disclaimer headers and module docstrings to all source and test files

### Changed

- Moved `calc_mcp_client.py` from `src/math_ai_agent/` to `tests/integration/` (integration test utility, not part of the distributed package)
- Updated `main.py` with module docstring, endpoint docstrings, and return type annotations
- Updated README.md, CLAUDE.md, and llms.txt to reflect new project structure

## [0.0.4] - 2026-03-06

### Added

- MCP client module (`calc_mcp_client.py`) with OAuth-authenticated connection to remote calculator MCP server
- Configuration module (`config.py`) loading settings from `config.yaml` with environment variable override
- YAML configuration file (`config.yaml`) for server, OAuth, and logging settings
- Unit tests for `config.py` (11 tests) and `calc_mcp_client.py` (10 tests)
- CLAUDE.md with project conventions and instructions for Claude Code
- `llms.txt` with LLM-friendly project documentation
- `py-key-value-aio[disk]` runtime dependency for encrypted OAuth token storage

### Changed

- Removed unused imports (`Annotated`, `Form`) from `main.py`
- Changed `httpx` logger level from DEBUG to INFO in `config.yaml`
- Updated README.md with current project structure and documentation
- Updated SETUP.md with current tool versions and instructions
- Reformatted test files to comply with black line-length rules

## [0.0.3] - 2026-02-21

### Changed

- Version bump to 0.0.3
- Updated release plan documentation

## [0.0.2] - 2026-02-21

### Added

- FastAPI web application with root endpoint serving HTML UI
- POST `/prompt/` endpoint accepting math questions via JSON
- MathQuestion Pydantic model for request validation
- Static file serving for frontend assets
- Bootstrap-based dark theme frontend with question/response form
- Comprehensive test suite (14 tests) covering endpoints, validation, and model

## [0.0.1] - 2026-02-20

### Added

- Initial project scaffolding with Poetry build system
- Project structure with `src/math_ai_agent` package layout
- Development tooling: pytest, mypy, black, isort, pylint, coverage
- GitHub connectivity test script (`scripts/test_github.sh`)
- CHANGELOG, LICENSE, README, and SETUP documentation

