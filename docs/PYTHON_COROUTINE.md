<!--
This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
-->

# Performance

This page explains the Python async event loop, and why every request can
safely share one LLM client and one MCP connection.

## The Python Async Event Loop

### The Problem It Solves

Almost all the time spent answering a prompt is waiting: for the LLM to
reply over the network and for the calculator MCP server to return a
result. The CPU does very little work.

A plain (synchronous) program blocks while it waits, so it serves one user
at a time. Threads solve that by running many blocking calls at once, but
each thread costs memory and the OS must switch between them. The async
event loop instead serves many users from one thread by never blocking on
a wait.

### Coroutines and `await`

A function defined with `async def` is a coroutine function. Calling it
does not run it; it returns a coroutine object that the event loop runs.

```python
async def run(self, user_prompt: str) -> str:
    response = await llm.create_response(history)
    ...
```

`await` marks a point where the coroutine may pause. When the awaited
operation must wait for I/O, the coroutine is suspended and control
returns to the event loop. The coroutine keeps its local variables and
resumes at the same line once the I/O completes.

### What the Event Loop Does

The event loop is a scheduler running in a single thread. In a loop, it:

1. Runs each ready task until that task reaches an `await` that has to
   wait.
2. Registers the task's pending I/O (a socket read, for example) with the
   OS. The OS reports when data arrives, through `kqueue` on macOS or
   `epoll` on Linux.
3. Asks the OS which pending I/O is now ready, and marks the tasks waiting
   on it as ready again.
4. Repeats.

A task is a coroutine scheduled on the loop. uvicorn creates one task for
each incoming HTTP request.

This is cooperative multitasking: a task gives up control only at an
`await`. Nothing pre-empts it, so no two tasks ever run Python code at the
same moment.

### Two Users on One Thread

Two users submit prompts at nearly the same time. Each prompt needs one
LLM call (about 2 seconds) and one tool call (about 0.1 seconds):

```text
time -->
Task A: [send LLM req] ....wait 2s.... [send tool call] .wait. [reply A]
Task B:   [send LLM req] ....wait 2s.... [send tool call] .wait. [reply B]
Loop:   runs A, runs B, waits on OS, resumes A, resumes B, ...
```

Both users get their answer after about 2.1 seconds, not 4.2 seconds. The
thread only runs Python code in the short bracketed steps and is free
during the waits.

### The Rule: Never Block the Loop

Because one thread runs every task, a call that blocks without `await`
stops all users at once. Examples are `time.sleep()`, the `requests`
library, or a long CPU-bound calculation. This project uses async
libraries for its network I/O: `AsyncOpenAI` (built on `httpx`) and
`fastmcp`.

Small blocking work, such as logging or reading the short `index.html`
file, is harmless. FastAPI runs plain `def` endpoints in a thread pool so
they do not block the loop. The `async def` endpoints in this app run on
the loop directly.

### How This App Runs

`poetry run math-ai-agent` starts uvicorn with one worker process, which
runs one event loop. At startup, the loop runs the app's `lifespan`, which
opens the MCP connection and builds the `Agent`. After that, every
`POST /prompt/` request becomes a task that runs `Agent.run()`. Its awaits
on the LLM and on MCP tool calls are where the loop switches to other
users.

## Why Sharing Is Safe

- **No user data on shared objects.** Each call to `Agent.run()` keeps the
  conversation history in a local variable. The `Agent` only holds objects
  that never change after startup: the two clients and the system
  instructions. One user's messages cannot leak into another user's
  request.
- **No races on Python state.** Tasks switch only at `await`, so no task
  can see another task's half-finished update.
- **The OpenAI client is built to be shared.** `AsyncOpenAI` is designed
  for concurrent use, and OpenAI recommends creating one client and reusing
  it.
- **The MCP client supports concurrent calls.** The `fastmcp` `Client`
  (v4.0.10) documents concurrent use and guards its session state with
  locks. Each tool call is a separate protocol request with its own ID,
  sent as its own HTTP request.

## Why Sharing Does Not Hurt Performance

- **Requests do not wait on each other.** While one request waits for the
  LLM or a tool, the loop serves other requests.
- **The LLM client uses a connection pool.** `AsyncOpenAI` keeps up to
  1,000 connections and reuses up to 100 idle ones. Concurrent requests
  get separate connections, so one shared client is not a single lane.
- **Tool calls run in parallel.** Tool calls from different users go out
  as separate HTTP requests over the shared MCP session. How many the MCP
  server processes at once depends on the server.
- **Sharing removes work.** A client per request would repeat connection
  setup, TLS handshakes, and the MCP session start (including OAuth) for
  every prompt. The shared clients do this once, at startup.

## Real Limits

These limits come from outside the shared clients:

- **The LLM provider.** Each prompt makes several LLM calls, so the
  provider's rate limits and latency are the first bottleneck.
- **The MCP server.** Its capacity caps how fast tool calls return.

The app guards against them with:

- **Reconnect.** If the MCP connection drops during a tool call,
  `CalcMCPConnection` reconnects once and retries the call.
- **`llm.max_concurrent_prompts`.** Prompts beyond this limit get HTTP
  503 at once instead of piling up.
- **`llm.timeout_seconds`.** Each LLM call fails after this many seconds.

This app has not been load-tested.
