# Plan: Move System Instructions to config.yaml

Move the `_SYSTEM_INSTRUCTIONS` text from `llm/agent.py` into a new
`llm.system_instructions` property in `config.yaml`.

## Steps

1. Add `llm.system_instructions` to `src/math_ai_agent/config/config.yaml`
   and to `../../config/config_local.yaml` and `../../config/config_remote.yaml`,
   using a folded block scalar (`>-`) so the text stays one line at runtime.
2. Add `get_system_instructions()` to `config/config.py`, following the
   pattern of `get_model()`. The key is required.
3. In `llm/agent.py`, import it and set
   `_SYSTEM_INSTRUCTIONS = get_system_instructions()`.
4. Add `system_instructions` to the `tmp_config` fixture in
   `tests/test_config.py` and add `test_get_system_instructions`.
5. Add a `Changed` entry under `[Unreleased]` in `CHANGELOG.md`.

## Verification

- Run `poetry run pytest tests --ignore=tests/integration`.
