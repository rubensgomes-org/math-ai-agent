# =============================================================================
# Math AI Agent — multi-stage container image.
#
#   builder : installs the pinned runtime dependencies from poetry.lock into
#             /opt/venv, builds the project wheel, and installs that wheel
#             into the same virtual environment.
#   runtime : the same base image, running as a non-root user, carrying only
#             /opt/venv and config/config_docker.yaml.
#
# Build:  docker build --build-arg APP_VERSION="$(poetry version -s)" \
#             -t "math-ai-agent:$(poetry version -s)" -t math-ai-agent:latest .
# Run:    docker run --rm -e NVIDIA_API_KEY -p 9090:8080 math-ai-agent
#         (expects calculator-mcp on Docker host port 8080; override the
#         config with -v <file>:/etc/math-ai-agent/config.yaml:ro)
# Verify: curl http://127.0.0.1:9090/health   ->   OK
#
# This project's source code and documentation were generated with the
# assistance of Artificial Intelligence (AI). For more information, please
# refer to the `AI_DISCLAIMER.md` document located in the project's root
# directory.
# =============================================================================

# Both stages MUST use the identical base image. The runtime stage copies the
# virtual environment verbatim, so its pyvenv.cfg and console-script shebangs
# must keep pointing at the same interpreter.
ARG PYTHON_IMAGE=python:3.14-slim-trixie

# -----------------------------------------------------------------------------
# Stage 1 — builder
# -----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

# Bundles poetry-core 2.5+, required by pyproject.toml [build-system].
ARG POETRY_VERSION=2.5.1

# PYTHONUNBUFFERED=1: sends stdout and stderr straight out without buffering,
#   so logs show up right away.
# NO_COLOR: disables ANSI color codes in log output.
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    POETRY_NO_INTERACTION=1 \
    POETRY_NO_ANSI=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    NO_COLOR=true

WORKDIR /build

# Poetry honours VIRTUAL_ENV and installs into it.
RUN python -m venv /opt/venv

# Poetry goes into the system interpreter so it never reaches the runtime
# image. No --mount=type=cache, so the build also works without BuildKit.
RUN /usr/local/bin/python -m pip install "poetry==${POETRY_VERSION}"

# --- dependency layer: invalidated only by pyproject.toml / poetry.lock ------
COPY pyproject.toml poetry.lock ./

# pyproject.toml declares readme = "README.md". A placeholder keeps README
# edits from invalidating the dependency layer.
RUN touch README.md

# poetry check --lock fails the build when poetry.lock is stale.
# --no-root defers installing the project itself to the wheel below.
RUN poetry check --lock \
 && poetry install --only main --no-root

# --- project layer: invalidated by source changes ---------------------------
COPY README.md LICENSE ./
COPY src ./src

RUN poetry build --format wheel

# config.yaml and index.html are package data read at run time, so a
# packaging regression would only surface in the running container.
RUN python -c "import glob, zipfile; \
w = glob.glob('dist/*.whl')[0]; \
names = zipfile.ZipFile(w).namelist(); \
required = ['math_ai_agent/config/config.yaml', \
            'math_ai_agent/static/index.html']; \
missing = [n for n in required if n not in names]; \
assert not missing, missing; \
print('OK: package data present in', w)"

# Dependencies are already pinned above, so --no-deps --no-index guarantees
# this step resolves nothing over the network.
RUN /opt/venv/bin/pip install --no-cache-dir --no-deps --no-index dist/*.whl

# Smoke-test the built artifact before it reaches the runtime stage.
RUN /opt/venv/bin/math-ai-agent --version

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# -----------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

# Deliberately not a real version; pass --build-arg APP_VERSION="$(poetry
# version -s)" so the OCI label matches pyproject.toml.
ARG APP_VERSION=0.0.0-dev

LABEL org.opencontainers.image.title="math-ai-agent" \
      org.opencontainers.image.description="Math AI Agent that uses LLM + Rubens calculator-mcp" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/rubensgomes-org/math-ai-agent" \
      org.opencontainers.image.url="https://github.com/rubensgomes-org/math-ai-agent" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Rubens Gomes <rubens.s.gomes@gmail.com>"

# PYTHONFAULTHANDLER=1: prints a traceback on fatal signals (e.g. segfault).
# MATHAIAGENT_CONFIG: the container config; mount a file here to override it.
# NO_COLOR: disables ANSI color codes in log output.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    HOME=/home/app \
    MATHAIAGENT_CONFIG=/etc/math-ai-agent/config.yaml \
    NO_COLOR=true

# Non-root service account with a fixed uid/gid, stable for volume ownership
# and for Kubernetes runAsUser.
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid 1001 \
            --create-home --home-dir /home/app \
            --shell /usr/sbin/nologin app

# Owned by root and readable by everyone: the application cannot mutate its
# own dependencies or configuration.
COPY --from=builder --chown=root:root /opt/venv /opt/venv
COPY --chown=root:root config/config_docker.yaml /etc/math-ai-agent/config.yaml

USER app
WORKDIR /home/app

# EXPOSE is not used by Azure Container Apps (ACA). Traffic reaches the
# container through the ingress targetPort set on the container app.
# Left this setting here to be used by `docker run`.
EXPOSE 8080

# HEALTHCHECK is ignored by Azure Container Apps (ACA). ACA runs on Kubernetes,
# which doesn't run the Docker HEALTHCHECK baked into an image. It uses its
# own probes instead.
# Left this setting here to be used by `docker ps`.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4); sys.exit(0 if r.status == 200 and r.read() == b'OK' else 1)"]

# Exec form: the console script is PID 1 and receives SIGTERM directly, and
# `docker run` arguments (e.g. --version) are appended to it.
ENTRYPOINT ["math-ai-agent"]
