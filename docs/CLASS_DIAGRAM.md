# Class Diagram

```text

payload.py                       llm/agent.py
┌──────────────────────┐         ┌──────────────────────────────────┐
│ Payload              │         │ Agent                            │
│  ──▷ [BaseModel]     │         │  _calc  ◆── CalcMCPConnection    │
│  text                │         │  _llm   ◆── ChatCompletionClient │
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

llm/client.py
                  ┌──────────────────────────────┐
                  │ _BaseLLMClient               │
                  │  openai_client ◆── [AsyncOpenAI]
                  │  model, tools, temperature   │
                  └──────────────▲───────────────┘
                   ┌─────────────┴──────────────┐
      ┌────────────┴────────────┐   ┌───────────┴─────────────┐
      │ ChatCompletionClient    │   │ ResponsesClient         │
      │  create_response()      │   │  stateful               │
      │  → /v1/chat/completions │   │  create_response()      │
      └─────────────────────────┘   │  → /v1/responses        │
  Chat Completions API: March 2023  └─────────────────────────┘
                                     Responses API: March 2025

mcp/calc_connection.py                     mcp/calc_client.py
┌───────────────────────────────────┐      ┌───────────────────────────────────┐
│ CalcMCPConnection                 │      │ CalcMCPClient                     │
│  _client ◆── 0..1 CalcMCPClient ──┼────▶ │  ──▷ [fastmcp.Client]             │
│  _client_factory (builds it)      │      │  auth ◆── [OAuth] (optional)      │
│  _reconnect_lock ◆── [Lock]       │      │  __init__ ···> AppConfig          │
│  call_tool() (reconnect+retry)    │      │            .server.calculator_mcp │
│  to_chat_completions_tools()      │      │  to_chat_completions_tools()      │
│  to_responses_tools()             │      │  to_responses_tools()             │
└───────────────────────────────────┘      └───────────────────────────────────┘
```