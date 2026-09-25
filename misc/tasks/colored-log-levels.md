# Plan: Colored Log Level Names

Color `%(levelname)s` in console logs (e.g. `[INFO]`) by level using
`colorlog`.

## Steps

1. Add the `colorlog` dependency with `poetry add colorlog`.
2. In `src/math_ai_agent/config/config.yaml`, `config/config_local.yaml`, and
   `config/config_remote.yaml`, make the `standard` formatter a
   `colorlog.ColoredFormatter` with `stream: ext://sys.stderr`, wrapping
   `[%(levelname)s]` in `%(log_color)s` and `%(reset)s`.
3. Add an `Added` entry under `[Unreleased]` in `CHANGELOG.md`.

## Verification

- Run `poetry run pytest tests --ignore=tests/integration`.
- Level names are colored in a terminal, and plain when piped or when
  `NO_COLOR` is set.
