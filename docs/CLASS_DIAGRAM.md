# Class Diagram

```text

schemas.py                       agent/agent.py
┌──────────────────────────┐     ┌──────────────────────────────────┐
│ PromptRequest            │     │ Agent                            │
│  ──▷ [BaseModel]         │     │  _calc  ◆── CalcMCPClient        │
│  text                    │     │  _llm   ◆── ChatCompletionsClient│
│  display_reasoning       │     │             | ResponsesClient    │
└──────────────────────────┘     │  _model ◆── Model                │
agent/errors.py                  │  _prompt_slots ◆── [Semaphore]   │
┌──────────────────────────┐     │  run() raises AgentError         │
│ AgentError               │     └──────────────────────────────────┘
│  ──▷ [RuntimeError]      │
│ ──▷ AgentError           │
│  AgentBusyError          │
│  TokenLimitError         │
│  ContentFilterError      │
│  LLMRequestFailedError   │
│  MaxTurnsExceededError   │
│  UnexpectedResponseError │
│ ──▷ LLMRequestFailedError│
│  LLMRateLimitedError     │
└──────────────────────────┘

llm/llm_client.py, llm/chat_completions_client.py, llm/responses_client.py
                  ┌──────────────────────────────┐
                  │ «abstract» LLMClient         │
                  │  openai_client ◆── [AsyncOpenAI]
                  │  model_name, tools           │
                  │  log_token_usage()           │
                  │  _token_usage()              │
                  └──────────────▲───────────────┘
                   ┌─────────────┴──────────────┐
      ┌────────────┴────────────┐   ┌───────────┴─────────────┐
      │ ChatCompletionsClient   │   │ ResponsesClient         │
      │  _format_tools()        │   │  _format_tools()        │
      │  prompt()               │   │  is_stateful            │
      │  → /v1/chat/completions │   │  prompt()               │
      └─────────────────────────┘   │  → /v1/responses        │
  Chat Completions API: March 2023  └─────────────────────────┘
                                     Responses API: March 2025

mcp/calc_client.py
┌───────────────────────────────────┐
│ CalcMCPClient                     │
│  ──▷ [fastmcp.Client]             │
│  auth ◆── [OAuth] (optional)      │
│  __init__(config: MCP)            │
│  timeout, init_timeout            │
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
