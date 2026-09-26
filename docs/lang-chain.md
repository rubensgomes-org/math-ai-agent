# Using LangChain with the NVIDIA Nemotron Model

**Date:** 2026-09-11 **Status:** Research notes / design sketch — not yet
implemented

Notes on whether the LangChain APIs can drive the
`nvidia/nemotron-3-super-120b-a12b` model configured in `config.yaml`, and
how `create_agent()` would be called in this project.

## Short Answer

Yes, it works, and `config.yaml` needs no changes.

`https://integrate.api.nvidia.com/v1` is OpenAI-compatible — which is exactly
why `src/math_ai_agent/llm/client.py` can point `AsyncOpenAI` at it. LangChain's
`ChatOpenAI` accepts the same `base_url` + `api_key`, so
`nvidia/nemotron-3-super-120b-a12b` is reachable as a LangChain chat model.

## Choosing the Model Class

| Class        | Package (latest on PyPI)              | Notes                                                                                                                                          |
|--------------|---------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `ChatOpenAI` | `langchain-openai` 1.6.2              | Drives either `/v1/chat/completions` or `/v1/responses` (`use_responses_api=True`), so the existing `llm.api_style` setting keeps its meaning. |
| `ChatNVIDIA` | `langchain-nvidia-ai-endpoints` 1.4.3 | NVIDIA-native, but Chat Completions only — `api_style: "responses"` would become dead config.                                                  |

**Recommendation:** `ChatOpenAI`. It preserves the `api_style` switch already
built into the project.

## The Tools Question

This is the real design decision.

`create_agent()` expects LangChain `BaseTool` objects, not OpenAI JSON tool
schemas. So the schemas produced by `CalcMCPClient.to_openai_tools()` and
`to_responses_tools()` are not directly usable.

Two options:

1. **`langchain-mcp-adapters`** (0.3.2) — talks to the MCP server directly.
   Rejected: it bypasses `CalcMCPClient`, and with it the FastMCP OAuth flow,
   the Fernet-encrypted token store, and the class-level tool cache.
2. **Wrap `call_tool` in `StructuredTool`** — keeps `CalcMCPClient` as the
   transport and feeds each MCP `inputSchema` straight in as `args_schema`
   (LangChain accepts a raw JSON-Schema dict there).

Option 2 is the cleaner path: it reuses the already-tested OAuth and MCP code
path unchanged.

## How `create_agent()` Would Be Called

```python
# src/math_ai_agent/llm/lc_agent.py  (+ the standard disclaimer header)
from functools import partial
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from math_ai_agent.config.config import (
    get_api_key,
    get_api_style,
    get_model,
    get_model_base_url,
)
from math_ai_agent.mcp.calc_client import CalcMCPClient, call_tool


async def _build_tools() -> list[StructuredTool]:
    """Wrap each calculator MCP tool as a LangChain StructuredTool."""
    async with CalcMCPClient() as calc:
        mcp_tools = await calc.list_tools()

    async def _run(tool_name: str, **kwargs: Any) -> str:
        return await call_tool(tool_name, kwargs)

    return [
        StructuredTool.from_function(
            coroutine=partial(_run, t.name),
            name=t.name,
            description=t.description or t.name,
            args_schema=t.inputSchema,  # MCP JSON Schema, used as-is
        )
        for t in mcp_tools
    ]


async def lc_agent_loop(user_prompt: str) -> str:
    """Run the agent loop via LangChain's create_agent."""
    model = ChatOpenAI(
        model=get_model(),  # nvidia/nemotron-3-super-120b-a12b
        base_url=get_model_base_url(),  # https://integrate.api.nvidia.com/v1
        api_key=get_api_key(),  # from NVIDIA_API_KEY
        use_responses_api=(get_api_style() == "responses"),
        store=False,  # keep the no-retention stance
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=await _build_tools(),
        system_prompt=_SYSTEM_INSTRUCTIONS,  # reuse the one in agent.py
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_prompt}]}
    )
    return result["messages"][-1].content or ""
```

### Key Points

- `create_agent()` itself is **synchronous** — it compiles a LangGraph graph —
  but tool discovery is async, so the agent has to be built inside an async
  function, as above.
- The compiled graph is invoked with `ainvoke`.
- The ReAct loop that `create_agent()` provides (call model → dispatch tool
  calls → feed results back → repeat until no tool calls) replaces both
  `_chat_agent_loop` and `_responses_agent_loop` wholesale.
- The system prompt goes in as `system_prompt=`; no manual seeding of a
  `{"role": "system", ...}` history entry.

### Dependencies

```bash
poetry add "langchain@^1.4.0" "langchain-openai@^1.6.0"
```

## Things to Watch

1. **The existing error handling disappears.** The `match finish_reason` and
   `match response.status` blocks in `llm/agent.py` — token limit,
   `content_filter`, unknown status — are hand-written. `create_agent()` just
   returns messages. To keep those `RuntimeError`s, inspect
   `response_metadata["finish_reason"]` on the final `AIMessage`, or write
   LangChain middleware.
2. **A connection per tool call.** `call_tool()` opens a fresh
   `CalcMCPClient` on every invocation. That is already true today, but
   LangChain does not fix it.
3. **Nemotron is a reasoning model.** Its `reasoning_content` lands in
   `additional_kwargs`, not `content`. The "plain text only, no LaTeX"
   instruction still matters and still belongs in `system_prompt`.
4. **Coverage floor of 90%.** A new `lc_agent.py` needs unit tests with a fake
   chat model, alongside the existing `tests/test_responses.py` and
   `tests/test_chat_completion.py`.

## Possible Next Step

Implement this as a third `llm.api_style` value (e.g. `langchain`) dispatched
from `agent_loop()` in `llm/agent.py`, so all three paths stay switchable from
`config.yaml`.
