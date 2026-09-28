# Math AI Agent

[![python](https://img.shields.io/badge/python-3.14.7-0969da)](https://www.python.org/downloads/release/python-3147/)
[![License](https://img.shields.io/badge/License-MIT-0969da)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE)
[![AI--Assisted](https://img.shields.io/badge/AI--Assisted-Development-8250df)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/AI_DISCLAIMER.md)

A prompt chat webapp that drives an LLM call inside an agentic loop using
the `calculator_mcp` MCP server for arithmetic operations. The key constraint is
that the LLM is given explicit system instructions to use `calculator_mcp` for
any arithmetic operations.

---

## Features

- **FastAPI web UI** — simple form-based interface for submitting prompts
- **MCP client** — connects to a remote calculator MCP server with optional
  OAuth authentication
- **Configurable** — MCP server URL, OAuth settings, LLM endpoint and model,
  and logging are all driven by `config.yaml`
- **Plain-text answers** — the model is instructed to reply without LaTeX or
  Markdown, since the web UI renders answers in a plain `<textarea>`

## Unsupported Features

- **Server-sent events (SSE)** are not supported for either LLM or MCP
  communication.
- **Streaming communication channels**, such as HTTP Streamable, are not
  supported. In other words, both the LLM model and the MCP server are expected
  to generate the entire output before sending it.
- **Stateful Responses API** communication may not be supported, depending on
  the LLM model selected in the configuration.
- **Input types** such as images and videos are not supported. Only text
  input is supported.
- **Tools** available to the LLM are limited to `calculator_mcp`. Other
  tool types, such as `built-in tools` (for example, web search and file search)
  and `function calls`, are not supported.

Bear in mind that support for the features listed above also depends on the
capabilities of the selected LLM model. For example, the default configured
model, NVIDIA Nemotron 3 Super, does not support storing conversation history
and supports only text input.

## AI Disclaimer

This project includes code and documentation created with the assistance of AI
tools. For details on usage, limits, and review practices, please see the
[AI Disclaimer](https://github.com/rubensgomes-org/math-ai-agent/blob/main/AI_DISCLAIMER.md).

## Prerequisites

- Python 3.14+
- pip

## Installation

1. Install in the default `pip` location

```bash
pip install math-ai-agent
```

2. Alternatively, install in the Python user directory

```bash
pip --no-cache-dir install -U --user math-ai-agent
```

3. Confirm the installed version matches the latest GitHub release at
   [math-ai-agent/releases](https://github.com/rubensgomes-org/math-ai-agent/releases)

```bash
math-ai-agent --version
pip show math-ai-agent
```

## Uninstall

- Uninstall as follows:

```bash
pip uninstall math-ai-agent
pip cache purge
```

## Configuration

### `calculator-mcp` Running Locally

- Copy the file
  [config_local.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/config/config_local.yaml)
  to `${HOME}/cfg/math-ai-agent/config_local.yaml`

- Set `MATHAIAGENT_CONFIG` for `calculator-mcp` running locally

```bash
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_local.yaml"
```

- Launch `calculator-mcp` locally following the instructions at
  [calculator-mcp](https://github.com/rubensgomes-org/calculator-mcp)

### `calculator-mcp` Running Remotely

**Note**: This requires OAuth authentication using a GitHub account. Currently,
only the project author is authorized.

- Copy the file
  [config_remote.yaml](https://github.com/rubensgomes-org/math-ai-agent/blob/main/config/config_remote.yaml)
  to `${HOME}/cfg/math-ai-agent/config_remote.yaml`

- Set `MATHAIAGENT_CONFIG` for `calculator-mcp` running remotely

```bash
export MATHAIAGENT_CONFIG="${HOME}/cfg/math-ai-agent/config_remote.yaml"
```

## Usage

- Run:

```bash
math-ai-agent
```

## License

The project is licensed under the
[MIT License](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE).

---
Author: [Rubens Gomes](https://rubensgomes.com/)
