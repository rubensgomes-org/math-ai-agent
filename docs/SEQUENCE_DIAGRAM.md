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
    participant Client as CalcMCPClient
    participant Transport as StreamableHttpTransport
    participant Session as mcp.ClientSession
    participant Http as httpx2.AsyncClient
    participant Server as Calculator MCP server

    Note over App,Server: Startup (FastAPI lifespan)
    App->>Client: create
    Client->>Transport: create (from the configured URL)
    App->>Client: __aenter__()
    Client->>Transport: connect_session()
    Transport->>Http: create (new connection pool)
    Transport->>Session: create
    Client->>Session: initialize()
    Session->>Http: POST initialize
    Http->>Server: HTTP request
    App->>Agent: Agent(calc).__aenter__()
    Agent->>Client: tools_definitions()
    Client->>Session: list_tools()
    Session->>Http: POST tools/list
    Http->>Server: HTTP request (pooled connection)
    Agent->>Agent: format_tools() and create the LLM client

    Note over App,Server: Each prompt (POST /prompt/)
    App->>Agent: run(prompt)
    loop Each tool call the LLM requests
        Agent->>Client: call_tool(name, args)
        Client->>Session: call_tool(name, args)
        Session->>Http: POST tools/call
        Http->>Server: HTTP request (pooled connection)
        Server-->>Agent: tool result, back through each layer
    end
    Agent-->>App: answer

    Note over App,Server: Shutdown (FastAPI lifespan)
    App->>Client: __aexit__() closes session and connection pool
```
