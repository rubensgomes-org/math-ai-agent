# Running the Math AI Agent with Docker

This document covers building and running the Math AI Agent web app as a
`docker` container.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.

## Overview

The image runs the FastAPI web app, which connects to the Calculator MCP
Server as a client.

| Property        | Value                                          |
|-----------------|------------------------------------------------|
| Base image      | `python:3.14-slim-trixie`                      |
| Listen address  | `0.0.0.0:8080` (inside the container)          |
| Published port  | `9090` on the host (maps to `8080`)            |
| Web page        | `http://<host>:9090/`                          |
| Health endpoint | `http://<host>:9090/health` (returns `OK`)     |
| Config file     | `/etc/math-ai-agent/config.yaml`               |
| MCP server      | `http://host.docker.internal:8080/mcp`         |
| User            | non-root, `uid=1001 gid=1001` (`app`)          |
| Image size      | ~346 MB                                        |
| Logs            | stderr only, visible via `docker logs`         |

## Prerequisites

- Docker Engine 23+ (or Docker Desktop) with the **buildx** and **compose**
  plugins.
- `NVIDIA_API_KEY` exported in the shell.
- `calculator-mcp` running on host port `8080`.

## Quick start

### Install `docker` CLI

- OS: `macOS`

    ```bash
    brew install docker
    ```

- Verify the toolchain:

    ```bash
    docker --version
    docker buildx version
    docker compose version
    ```

### Install `Docker Desktop`

- Follow
  [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)

### Using `docker` commands

- Start the `Docker Desktop` GUI + engine

    ```bash
    # macOS
    open -a Docker
    ```

- Build the docker image

    ```bash
    docker build --build-arg APP_VERSION="$(poetry version -s)" \
        -t "math-ai-agent:$(poetry version -s)" -t math-ai-agent:latest .
    ```

- Launch container from built image

    ```bash
    docker run -d --name math-ai-agent -e NVIDIA_API_KEY -p 9090:8080 \
        --restart unless-stopped "math-ai-agent:$(poetry version -s)"

    # Verify - expect OK
    curl http://127.0.0.1:9090/health
    ```

- To use another config, mount it over the bundled one:

    ```bash
    docker run -d --name math-ai-agent -e NVIDIA_API_KEY -p 9090:8080 \
        -v "$PWD/my-config.yaml:/etc/math-ai-agent/config.yaml:ro" \
        "math-ai-agent:$(poetry version -s)"
    ```

- To stop the running container:

    ```bash
    docker stop math-ai-agent
    docker rm math-ai-agent
    ```

### Using `docker compose` commands

- Build and launch container

    ```bash
    APP_VERSION="$(poetry version -s)" docker compose up --build -d
    docker compose ps
    # Verify - expect OK
    curl http://127.0.0.1:9090/health
    ```

- Display logs

    ```bash
    docker compose logs -f math-ai-agent
    ```

- Stop container

    ```bash
    docker compose down
    ```

## Using the app

Open `http://127.0.0.1:9090` in a browser.

## Multi-architecture builds

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
    --build-arg APP_VERSION="$(poetry version -s)" \
    -t "math-ai-agent:$(poetry version -s)" .
```

Building `linux/amd64` on Apple Silicon runs the builder stage under QEMU
emulation, which is correct but noticeably slower.
