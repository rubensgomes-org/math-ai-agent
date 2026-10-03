# MCP Client Sequence Diagram

When the MCP client classes are created, and how they interact at runtime.
The same diagram, for Lucidchart or draw.io, is in `mcp_sequence.drawio`.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.

```mermaid
sequenceDiagram
    participant App as app.py
    participant Agent
    participant Conn as CalcMCPClientMgr
    participant Client as CalcMCPClient
    participant Transport as StreamableHttpTransport
    participant Session as mcp.ClientSession
    participant Http as httpx2.AsyncClient
    participant Server as Calculator MCP server

    Note over App,Server: Startup (FastAPI lifespan)
    App->>Conn: create
    App->>Conn: __aenter__()
    Conn->>Client: create (client_factory)
    Client->>Transport: create (from the configured URL)
    Conn->>Client: __aenter__()
    Client->>Transport: connect_session()
    Transport->>Http: create (new connection pool)
    Transport->>Session: create
    Client->>Session: initialize()
    Session->>Http: POST initialize
    Http->>Server: HTTP request
    App->>Agent: Agent.create(calc)
    Agent->>Conn: to_chat_completions_tools() or to_responses_tools()
    Conn->>Client: same method
    Client->>Session: list_tools()
    Session->>Http: POST tools/list
    Http->>Server: HTTP request (pooled connection)
    Agent->>Agent: create the LLM client with the tools

    Note over App,Server: Each prompt (POST /prompt/)
    App->>Agent: run(prompt)
    loop Each tool call the LLM requests
        Agent->>Conn: call_tool(name, args)
        Conn->>Client: call_tool(name, args)
        Client->>Session: call_tool(name, args)
        Session->>Http: POST tools/call
        Http->>Server: HTTP request (pooled connection)
        Server-->>Agent: tool result, back through each layer
    end
    Agent-->>App: answer

    Note over App,Server: Session lost during call_tool()
    Conn->>Client: __aexit__() closes session and connection pool
    Conn->>Client: create a new client and __aenter__()
    Note right of Client: New Transport, Session, and httpx2.AsyncClient,<br/>as at startup
    Conn->>Client: call_tool(name, args), retried once

    Note over App,Server: Shutdown (FastAPI lifespan)
    App->>Conn: __aexit__()
    Conn->>Client: __aexit__() closes session and connection pool
```
