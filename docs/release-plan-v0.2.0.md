# Release Plan v0.2.0

**Repository:** `rubensgomes-org/math-ai-agent`
**Previous release:** v0.1.0 (2026-08-20)
**Target release:** v0.2.0
**Date:** 2026-08-21

## Summary

Adds OpenAI **Responses API** support alongside the existing Chat Completions
path, selectable with the new `llm.api_style` setting. Splits the LLM
sub-package into a transport layer (`llm/client.py`) and an orchestration layer
(`llm/agent.py`), and switches the default provider from OpenRouter to NVIDIA's
hosted API after OpenRouter's free tier proved too restrictive (50 requests per
day).

Both API paths are verified working end to end against the live NVIDIA endpoint
and the remote calculator MCP server.

## Pre-flight

- [x] Repository `rubensgomes-org/math-ai-agent` exists (PUBLIC, default
      branch `main`)
- [x] `scripts/test_github.sh rubensgomes-org/math-ai-agent` succeeds
      (8 passed, 0 failed, exit 0)
- [x] Project documentation updated for the recent code changes
      (`README.md`, `CLAUDE.md`, `llms.txt`, `OLLAMA.md`, `TODO.md`,
      both `config.yaml` copies)

## Release steps

- [x] 1. `poetry run mypy src/` — fix any issues
- [x] 2. `poetry run isort src/ tests/` — fix any issues
- [x] 3. `poetry run black src/ tests/` — fix any issues
- [x] 4. `poetry run pytest` — fix any issues
- [x] 5. `export SOURCE_DATE_EPOCH=$(date +%s); poetry build -v` — fix any
        issues
- [x] 6. Ensure `CHANGELOG.md` exists in the project root
- [x] 7. Update `CHANGELOG.md` with the current release changes
        (promote `[Unreleased]` to `[0.2.0] - 2026-08-21`)
- [ ] 8. Commit all changes to `main`, create tag `v0.2.0`, push, and create
        the GitHub release

## Release contents

### Added

- `ResponsesClient` (`llm/client.py`) for the OpenAI Responses API
  (`POST /v1/responses`)
- `_responses_agent_loop()` with stateless replay of output Items
- `llm.api_style` setting (`responses` | `chat`) and `get_api_style()`
- `CalcMCPClient.to_responses_tools()` for the flat Responses tool schema
- `tests/integration/test_llm_responses_tool.py`

### Changed

- `OpenAIClient` renamed to `ChatCompletionClient`
- `llm/llm.py` split into `llm/client.py` + `llm/agent.py`; `agent_loop`
  re-exported from `math_ai_agent.llm`
- `get_mcp_tools()` renamed to `get_calc_mcp_tools()`
- Conversation-history parameter unified as `history`
- Both clients send `store=False`
- Default provider switched to NVIDIA
  (`https://integrate.api.nvidia.com/v1`)
- Test count 73 → 112, coverage held at 100%

## Verification performed before release

- Responses path: live tool-calling round trip against NVIDIA
  (`multiply` → `add` → final answer)
- Chat path: live, correct answer with `api_style: "chat"`
- `POST /prompt/` through FastAPI: HTTP 200 with correct answers
- MCP + OAuth: 16 tools discovered and dispatched

## Rollback

If the release needs to be withdrawn:

```bash
gh release delete v0.2.0 --repo rubensgomes-org/math-ai-agent --yes
git push --delete origin v0.2.0
git tag -d v0.2.0
```
