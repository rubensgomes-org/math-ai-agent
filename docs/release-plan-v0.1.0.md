# Release Plan v0.1.0

## Summary

First minor release. Brings test coverage from 74% to 100% — above the
configured 90% floor for the first time — by adding unit tests for
`agent_loop()`, which previously had none, and for the two module-level helpers
in `mcp/calc_client.py`. Also restores `uvicorn` as an explicit dev dependency.

Version bumped from 0.0.16 to 0.1.0 to mark this as a feature release rather
than another patch.

## Changes

### Added

- Unit tests for `agent_loop()` covering every `finish_reason` branch (`stop`,
  `length`, `tool_calls`, `content_filter`, `None`, and unknown), single and
  multiple tool-call dispatch, missing token usage, and empty content
- Unit tests for the `get_mcp_tools()` and `call_tool()` module helpers in
  `mcp/calc_client.py`, including error propagation
- `uvicorn` restored as an explicit dev dependency (`>=0.52.0,<0.53.0`); it was
  previously present only as a transitive of `fastmcp`

### Changed

- Test coverage raised from 74% to 100%, clearing the configured 90% floor
- Test count raised from 60 to 73
- Listed `uvicorn` among the dev tools in `llms.txt`

## Checklist

- [x] Run `poetry run mypy src/` and fix any issues
- [x] Run `poetry run isort src/ tests/` and fix any issues
- [x] Run `poetry run black src/ tests/` and fix any issues
- [x] Run `poetry run pytest` and fix any issues
- [x] Run `export SOURCE_DATE_EPOCH=$(date +%s); poetry build -v` and fix any issues
- [x] Verify `CHANGELOG.md` exists
- [x] Update `CHANGELOG.md` with v0.1.0 changes
- [x] Bump version to 0.1.0 in `pyproject.toml`
- [ ] Commit all changes, tag, push, and create GitHub release

## Notes

- No source code changed in this release — the diff against `v0.0.16` touches
  only tests, dependency metadata, the changelog, and docs. Runtime behaviour is
  identical to v0.0.16.
- `poetry run pytest --cov=src/` now passes the `fail_under = 90` gate, so the
  coverage variant is safe to run in CI. This was not true for any prior
  release.
- The `agent_loop()` tests are the first to exercise that function's control
  flow at all; every branch past `llm.py:193` was previously unverified.
