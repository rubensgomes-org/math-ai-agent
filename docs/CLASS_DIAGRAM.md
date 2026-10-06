# Class Diagram

```text

payload.py                       agent/agent.py
┌──────────────────────┐         ┌──────────────────────────────────┐
│ Payload              │         │ Agent                            │
│  ──▷ [BaseModel]     │         │  _calc  ◆── CalcMCPClient        │
│  text                │         │  _llm   ◆── ChatCompletionsClient│
│  display_reasoning   │         │             | ResponsesClient    │
└──────────────────────┘         │  _prompt_slots ◆── [Semaphore]   │
llm/llm_errors.py                │  create() ···> AppConfig.llm     │
┌──────────────────────┐         │  run() raises AgentBusyError     │
│ AgentBusyError       │         │    TokenLimitError               │
│ TokenLimitError      │         │    ContentFilterError            │
│ ContentFilterError   │         │    LLMRequestFailedError         │
│ LLMRequestFailedError│         └──────────────────────────────────┘
│  ──▷ [RuntimeError]  │
└──────────────────────┘

llm/llm_client.py, llm/chat_completions_client.py, llm/responses_client.py
                  ┌──────────────────────────────┐
                  │ «abstract» LLMClient         │
                  │  openai_client ◆── [AsyncOpenAI]
                  │  model, tools, temperature   │
                  │  format_tools()              │
                  │  prompt()                    │
                  │  report_usage()              │
                  └──────────────▲───────────────┘
                   ┌─────────────┴──────────────┐
      ┌────────────┴────────────┐   ┌───────────┴─────────────┐
      │ ChatCompletionsClient   │   │ ResponsesClient         │
      │  format_tools()         │   │  format_tools()         │
      │  prompt()               │   │  stateful               │
      │  → /v1/chat/completions │   │  prompt()               │
      └─────────────────────────┘   │  → /v1/responses        │
  Chat Completions API: March 2023  └─────────────────────────┘
                                     Responses API: March 2025

mcp/calc_client.py
┌───────────────────────────────────┐
│ CalcMCPClient                     │
│  ──▷ [fastmcp.Client]             │
│  auth ◆── [OAuth] (optional)      │
│  __init__ ···> AppConfig          │
│            .server.calculator_mcp │
│  tools_definitions()              │
└───────────────────────────────────┘
```
## MCP Client Layers

```text
mcp/calc_client.py
┌───────────────────────────────────────────────┐
│ CalcMCPClient                                 │
│  ──▷ [fastmcp.Client]                         │
│  transport ◆── [StreamableHttpTransport]      │
│  session   ◆── 0..1 [mcp.ClientSession]       │
│    (one MCP session while connected)          │
└───────────────────────┬───────────────────────┘
                        ▼
fastmcp
┌───────────────────────────────────────────────┐
│ [StreamableHttpTransport]                     │
│  connect_session() ···> [httpx2.AsyncClient]  │
│                    ···> [mcp.ClientSession]   │
│    (both created anew for each session)       │
└───────────────────────┬───────────────────────┘
                        ▼
httpx2
┌───────────────────────────────────────────────┐
│ [httpx2.AsyncClient]                          │
│  connection pool of keep-alive HTTP           │
│  connections to the server's /mcp endpoint    │
└───────────────────────────────────────────────┘
```
