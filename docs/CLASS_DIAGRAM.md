# Class Diagram

```text

payload.py                       llm/agent.py
┌──────────────────────┐         ┌──────────────────────────────────┐
│ Payload              │         │ Agent                            │
│  ──▷ [BaseModel]     │         │  _calc  ◆── CalcMCPClientMgr     │
│  text                │         │  _llm   ◆── ChatCompletionsClient│
│  display_reasoning   │         │             | ResponsesClient    │
└──────────────────────┘         │  _prompt_slots ◆── [Semaphore]   │
                                 │  create() ···> AppConfig.llm     │
┌──────────────────────┐         │  run() raises AgentBusyError     │
│ AgentBusyError       │         │    TokenLimitError               │
│ TokenLimitError      │         │    ContentFilterError            │
│ ContentFilterError   │         │    LLMRequestFailedError         │
│ LLMRequestFailedError│         └──────────────────────────────────┘
│  ──▷ [RuntimeError]  │
└──────────────────────┘

llm/llm_client.py, llm/chat_completions_client.py, llm/responses_client.py
                  ┌──────────────────────────────┐
                  │ LLMClient                    │
                  │  openai_client ◆── [AsyncOpenAI]
                  │  model, tools, temperature   │
                  └──────────────▲───────────────┘
                   ┌─────────────┴──────────────┐
      ┌────────────┴────────────┐   ┌───────────┴─────────────┐
      │ ChatCompletionsClient   │   │ ResponsesClient         │
      │  format_tools()         │   │  format_tools()         │
      │  create_response()      │   │  stateful               │
      │  → /v1/chat/completions │   │  create_response()      │
      └─────────────────────────┘   │  → /v1/responses        │
  Chat Completions API: March 2023  └─────────────────────────┘
                                     Responses API: March 2025

mcp/calc_client_mgr.py                     mcp/calc_client.py
┌───────────────────────────────────┐      ┌───────────────────────────────────┐
│ CalcMCPClientMgr                  │      │ CalcMCPClient                     │
│  _client ◆─ 0..1 CalcMCPClient    ┼────▶ │  ──▷ [fastmcp.Client]             │
│  _client_factory (builds it)      │      │  auth ◆── [OAuth] (optional)      │
│  _reconnect_lock ◆── [Lock]       │      │  __init__ ···> AppConfig          │
│  call_tool() (reconnect+retry)    │      │            .server.calculator_mcp │
│  tools_definitions()              │      │  tools_definitions()              │
└───────────────────────────────────┘      └───────────────────────────────────┘
```
## MCP Client Layers

```text
mcp/calc_client_mgr.py
┌───────────────────────────────────────────────┐
│ CalcMCPClientMgr                              │
│  _client ◆── 0..1 CalcMCPClient               │
│    (replaced by a new client on reconnect)    │
└───────────────────────┬───────────────────────┘
                        ▼
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
