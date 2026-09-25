# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
