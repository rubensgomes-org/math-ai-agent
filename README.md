[![python](https://img.shields.io/badge/python-3.14.7-0969da)](https://www.python.org/downloads/release/python-3147/)
[![License](https://img.shields.io/badge/License-MIT-0969da)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE)
[![AI--Assisted](https://img.shields.io/badge/AI--Assisted-Development-8250df)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/AI_DISCLAIMER.md)

# Math AI Agent

A prompt chat webapp that drives an LLM call inside an agentic loop using
the `calculator_mcp` MCP server for arithmetic operations. The key constraint is
that the LLM is given explicit system instructions to use the `calculator_mcp`
for any arithmetic operations.

## Features

- **FastAPI web UI** — simple form-based interface for submitting prompts
- **MCP client** — connects to a remote calculator MCP server with optional
  OAuth authentication
- **Configurable** — MCP server URL, OAuth settings, LLM endpoint and model,
  and logging are all driven by `config.yaml`
- **Plain-text answers** — the model is instructed to reply without LaTeX or
  Markdown, since the web UI renders answers in a plain `<textarea>`

## AI Disclaimer

This project includes code and documentation created with the assistance of AI
tools. For details on usage, limits, and review practices, please see the
[AI Disclaimer](https://github.com/rubensgomes-org/math-ai-agent/blob/main/AI_DISCLAIMER.md).

## Installation

### Prerequisites

- UNIX OS (e.g., macOS, Linux)
- curl 8.7+
- pip 26.2+
- poetry 2.4+
- python 3.14+

### PyPI Package Installation

**IMPORTANT**: release versioning was recently reset to start again at
version 0.0.1. Uninstall any previously installed version first.

1. Uninstall any previously installed release

```bash
pip uninstall math-ai-agent
# purging the cache is recommended as well
pip cache purge
```

2. Install into the user's home environment

```bash
# install "math-ai-agent" and dependencies into user local pip environment
# NOTE: use --no-cache-dir to avoid issues with an earlier cached version
pip --no-cache-dir install -U --user math-ai-agent --verbose
```

3. Confirm the installed version matches the latest GitHub release at
   [math-ai-agent/releases](https://github.com/rubensgomes-org/math-ai-agent/releases)

```bash
# show the installed version
pip show math-ai-agent
```

### Git Clone Installation

1. `git` clone and install local project package using `poetry`

```bash
# use local `dev` folder to install the project
mkdir -p ~/dev || exit; cd ~/dev
git clone https://github.com/rubensgomes-org/math-ai-agent.git
# change to project git local directory
cd math-ai-agent
# ensure we are at the project git local root folder
cd $(git rev-parse --show-toplevel) || exit
poetry install
```

## Usage

### Configuration

The server ships with a default
[config.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/src/math_ai_agent/config/config.yaml)
bundled inside the PyPI package. To override it, set the `MATHAIAGENT_CONFIG`
environment variable to the absolute path of your custom configuration file:

```bash
# assuming config_local.yaml placed in my home folder
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_local.yaml"
```

### Running Using PyPI Package

**NOTE:** requires prior installation using
`pip install -U --user math-ai-agent`.

1. Make a copy of
   [config_local.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/config/config_local.yaml)
   to a local home directory (e.g.,
   `${HOME}/cfg/math-ai-agent/config_local.yaml`).

2. Launch the PyPI-installed `math-ai-agent` package:

```bash
# config_local.yaml placed in my home folder
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_local.yaml"
# using installed package from PyPI:
math-ai-agent
```

3. Health check

```bash
# port is set by web.port in config_local.yaml
curl -v http://localhost:9090/health
# Expect: OK
```

4. To stop, go to the running terminal and press `Ctrl+C`

### Running Using Git Cloned Project - MCP Server Running Locally

**NOTE:** requires the `calculator_mcp` running locally as per instructions at
[calculator-mcp](https://github.com/rubensgomes-org/calculator-mcp)

1. Make a copy of
   [config_local.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/config/config_local.yaml)
   to a local home directory (e.g.,
   `${HOME}/cfg/math-ai-agent/config_local.yaml`).

2. Launch `math-ai-agent` from the local Git repo folder

```bash
# On my machine the project is installed here:
pushd ~/github/rubens/dev/python/math-ai-agent/
# ensure we are at the project git local root folder
cd $(git rev-parse --show-toplevel) || exit
# config_local.yaml placed in my home folder
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_local.yaml"
# ensure below port does not conflict with locally running MCP server.
poetry run math-ai-agent
```

3. Health check

```bash
curl -v http://localhost:9090/health
# Expect: OK
```

4. To stop, go to the running terminal and press `Ctrl+C`

### Calculator MCP Server Running Remotely - OAuth Authentication

**NOTE:** requires OAuth authentication which currently only Rubens is able to
authorize using his personal GitHub account.

1. Make a copy of
   [config_remote.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/config/config_remote.yaml)
   to a local home directory (e.g.,
   `${HOME}/cfg/math-ai-agent/config_remote.yaml`).

2. Launch `math-ai-agent` from the local Git repo folder

```bash
# On my machine the project is installed here:
pushd ~/github/rubens/dev/python/math-ai-agent/
# ensure we are at the project git local root folder
cd $(git rev-parse --show-toplevel) || exit
# config_remote.yaml placed in my home folder
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_remote.yaml"
# clean up previously created OAuth tokens
rm -fr ~/.calc-mcp-token
poetry run math-ai-agent
```

3. Health check

```bash
curl -v http://localhost:9090/health
# Expect: OK
```

4. To stop, go to the running terminal and press `Ctrl+C`

## License

The project is licensed under
[MIT License](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE).

---
Author: [Rubens Gomes](https://rubensgomes.com/)
