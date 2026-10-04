# Math AI Agent

[![python](https://img.shields.io/badge/python-3.14%2B-0969da?logo=python)](https://www.python.org/downloads/release/python-3147/)
[![poetry](https://img.shields.io/badge/poetry-2.5%2B-0969da?logo=poetry)](https://python-poetry.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.142%2B-8250df?logo=fastapi)](https://fastapi.tiangolo.com/)
[![FastMCP](https://img.shields.io/badge/FastMCP-4-8250df)](https://gofastmcp.com/getting-started/welcome)
[![OpenAI](https://img.shields.io/badge/OpenAI-3.22%2B-8250df?logo=openai)](https://github.com/openai/openai-python)
[![GitHub](https://img.shields.io/badge/GitHub-Actions-0969da?logo=github+actions)](https://github.com/features/actions)
[![Microsoft](https://img.shields.io/badge/Microsoft-Azure-0969da)](https://azure.microsoft.com/en-us)
[![AI](https://img.shields.io/badge/AI-Assisted-d29922?logo=claude+code)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/AI_DISCLAIMER.md)
[![license](https://img.shields.io/badge/license-MIT-1a7f37)](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE)

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
- **Streaming communication channels**, such as Streamable HTTP, are not
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

1. Install using `pip`

```bash
pip install math-ai-agent
```

2. Confirm the installed version matches the latest GitHub release at
   [math-ai-agent/releases](https://github.com/rubensgomes-org/math-ai-agent/releases)

```bash
math-ai-agent --version
pip show math-ai-agent
```

## Uninstall

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

### Overriding the `calculator-mcp` URL

A non-empty `CALCULATOR_MCP_URL` overrides `server.calculator_mcp.url`.

## Usage

1. Simply run

```bash
math-ai-agent
```

2. Health check

```bash
curl -v http://localhost:9090/health
# Expect: OK
```

3. To stop, go to the running terminal and press `Ctrl+C`. If `Ctrl+C` does
   not work you can try the following:

```bash
PID="$(pgrep -f math-ai-agent)"
kill -15 "${PID}"
```

## License

The project is licensed under the
[MIT License](https://github.com/rubensgomes-org/math-ai-agent/blob/main/LICENSE).

## Links

- [GitHub Project](https://github.com/rubensgomes-org/math-ai-agent)
- [Agent, LLM, MCP Diagram](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/AGENT_LLM_MCP_DIAGRAM.md)
- [Class Diagram](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/CLASS_DIAGRAM.md)
- [Development Setup](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/DEVELOPMENT_SETUP.md)
- [Docker](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/DOCKER.md)
- [LangChain Notes](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/lang-chain.md)
- [LLM Models](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/LLM_MODELS.md)
- [LLM Tool Calls and the MCP Server](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/LLM_MCP.md)
- [MCP Client Sequence Diagram](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/SEQUENCE_DIAGRAM.md)
- [OAuth Authentication Diagram](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/OAUTH_DIAGRAM.md)
- [Ollama LLM Models](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/OLLAMA.md)
- [PyCharm](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/PYCHARM.md)
- [Python Coroutines](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/PYTHON_COROUTINE.md)
- [Python Execution](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/PYTHON_EXECUTION.md)
- [Release Process](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/RELEASE.md)
- [Tests](https://github.com/rubensgomes-org/math-ai-agent/blob/main/docs/TESTS.md)

---
Author: [Rubens Gomes](https://rubensgomes.com/)
