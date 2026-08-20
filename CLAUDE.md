# CLAUDE.md

## Project Overview

Math AI Agent -- a Python application that uses an LLM with a remote calculator
MCP server to answer math questions via a FastAPI web interface.

## Build & Run

```bash
# Install dependencies
poetry install

# Run the FastAPI server
poetry run uvicorn math_ai_agent.app:app --reload

# Run the MCP integration test client
poetry run python tests/integration/test_calc_client.py
```

## Code Quality

```bash
# Type checking
poetry run mypy src/

# Sort imports
poetry run isort src/ tests/

# Lint
poetry run pylint src/ tests/

# Format code (line length 80)
poetry run black src/ tests/

# Run tests
poetry run pytest

# Run tests with coverage (minimum 90%)
poetry run pytest --cov=src/ --cov-report=term-missing

# Full cleanup
poetry run poe clean
```

## Project Conventions

- **Package layout:** `src/math_ai_agent/` with `config/`, `llm/`, and `mcp/`
  sub-packages; tests in `tests/`
- **Python version:** >= 3.14
- **Line length:** 80 (black + isort)
- **Formatting:** black with isort (profile "black")
- **Type checking:** mypy with `ignore_missing_imports = true`
- **Test framework:** pytest with `asyncio_mode = "auto"`
- **Coverage:** branch coverage, minimum 90% (`fail_under = 90`)
- **Build system:** Poetry 2.4+ with `poetry-core` backend

## Source File Headers

All source files include a disclaimer header with AI content notice, copyright
status, limitation of liability, and no-warranty disclaimer. New source files
must include this same header. Use the `/generate-disclaimer` skill to add it.

## Configuration

- Config is in `config.yaml` at the project root; the packaged default lives at
  `src/math_ai_agent/config/config.yaml`
- Resolution order: `CALCULATOR_MCP_CONFIG` env var, then `./config.yaml` in the
  cwd, then the packaged default
- OAuth requires `OAUTH_STORAGE_ENCRYPTION_KEY` (Fernet key)
- LLM endpoint and model come from the `llm:` block in `config.yaml`
- The LLM API key is read from the environment variable *named* by
  `llm.api_key_env` (currently `OPENROUTER_API_KEY`); never put the key itself
  in `config.yaml`

## Release Process

- Only Rubens Gomes is authorized to push releases
- Releases use the `/release-plan` slash command in Claude Code
- Release plans are saved in `docs/release-plan-v{VERSION}.md`
- Changelog follows Keep a Changelog format in `CHANGELOG.md`
