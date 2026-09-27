# OAuth Authentication Diagram

```text

                 ┌──────────────────┐
                 │  User's Browser  │
                 └───┬──────────┬───┘
                     │          │
                     │          │
┌────────────────────┴───┐    ┌─┴──────────────────────┐
│  math-ai-agent         │    │  GitHub                │
│  (OAuth client +       │    │  (Identity Provider)   │
│   callback :10000)     │    └─┬──────────────────────┘
└────────────────────┬───┘      │
                     │          │
                     │          │
                 ┌───┴──────────┴──────┐
                 │  Calculator MCP     │
                 │  Server (Horizon)   │
                 │  (Authorization +   │
                 │   Resource Server)  │
                 └─────────────────────┘
```