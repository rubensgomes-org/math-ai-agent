<!--
This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
-->

# LLM Tool Calls and the MCP Server

This page explains what a tool call in `llm/agent.py` refers to, which MCP
server runs it, how the two LLM APIs differ, what each request contains,
and the math inside the LLM.

## Tools Are Not MCP Servers

A tool is one function on the calculator MCP server, such as `add` or
`divide`. There is one MCP server with many tools.

At startup, the app fetches the server's tool list and sends it to the LLM
as function definitions. When the LLM wants a calculation, it replies with
a tool call. In both agent loops, `tool_call.name` (Responses API) or
`tool_call.function.name` (Chat Completions) is the name of one of those
tools.

`Agent._call_tool()` then sends the tool name and arguments to the MCP
server over the shared `CalcMCPConnection`.

## The Calculator MCP Server

The app uses one MCP server, set in the `server.calculator_mcp` section
of `config.yaml`:

| Detail | Value | Source |
|---|---|---|
| URL | `https://rubens-calculator-mcp.fastmcp.app/mcp` | `url` |
| Hosting | Prefect Horizon | comment above `url` |
| Transport | Streamable HTTP over HTTPS | built from `url` |
| Auth | OAuth | `is_oauth: true` |
| Name and version | Sent by the server on connect; not logged | the server |
| IP address | Resolved by DNS on each connection; not stored | DNS |

- **Name and version.** The name is the one the server passes to
  `FastMCP("...")` in its own code. After connecting, the client can read
  it from `client.server_info`.
- **IP address.** The host may sit behind a load balancer, so the address
  can change between connections. Look it up with
  `dig rubens-calculator-mcp.fastmcp.app`.

## Responses API vs. Chat Completions API

The app talks to the LLM through one of two OpenAI APIs, chosen by
`llm.api_style` in `config.yaml`. The Responses API is OpenAI's primary
API; Chat Completions is the older one, still supported and offered by
more providers.

| | Chat Completions (`chat`) | Responses (`responses`) |
|---|---|---|
| Endpoint | `POST /v1/chat/completions` | `POST /v1/responses` |
| Client | `ChatCompletionClient` | `ResponsesClient` |
| Conversation | `messages`: role/content dicts | `input`: typed items |
| System prompt | First message, role `system` | Top-level `instructions` |
| Tool schema | Nested under `function` | Flat: `name` at top level |
| Tool request | `message.tool_calls` | `function_call` output items |
| Tool result | Message with role `tool` | `function_call_output` item |
| Call ID field | `tool_call_id` | `call_id` |
| Loop control | `finish_reason` | `status` |
| Final text | `message.content` | `output_text` |
| Token usage | `prompt/completion_tokens` | `input/output_tokens` |
| Stored by default | No | Yes |

- **Loop control.** Chat Completions ends with a `finish_reason` of `stop`,
  `tool_calls`, `length`, or `content_filter`. Responses reports a
  `status` of `completed`, `incomplete` (with a reason), `failed`,
  `queued`, or `in_progress`. The answer is final when it is `completed`
  and has no `function_call` items.
- **State.** The Responses API can keep the conversation on the server and
  continue it with `previous_response_id`. This app does not use that: it
  sends `store=False` and replays every output item, including the
  model's reasoning items, on each turn. Some providers, such as
  OpenRouter, only support this stateless mode.
- **Tool schemas.** `CalcMCPClient.to_openai_tools()` builds the Chat
  Completions format and `to_responses_tools()` builds the Responses
  format from the same MCP tool list.

## System Instructions vs. User Prompt

Both are text sent to the LLM on every call, but they come from different
people and do different jobs:

| | System instructions | User prompt |
|---|---|---|
| Written by | The developer | The person using the app |
| Source | `llm.system_instructions` | The web page's question box |
| Changes | Only when `config.yaml` changes | With every request |
| Purpose | Rules: role, tone, format, tools | The task: the math question |
| Chat Completions | First message, role `system` | Message with role `user` |
| Responses | Top-level `instructions` | Input item with role `user` |
| Priority | Higher when the two conflict | Lower |

- **Where they go.** In `Agent._run_chat`, the system message is the first
  entry in `history`, followed by the user message. In
  `Agent._run_responses`, `history` starts with the user message, and the
  system instructions are sent separately on each call. Newer OpenAI
  models call the system role `developer`.
- **Why they are separate.** The system instructions stay the same for
  every user, so rules such as "For every math operation, request a tool
  call to the calculator" and "Respond in plain text only" apply to every
  question.
- **Priority is trained, not enforced.** Models are trained to follow the
  system instructions over a conflicting user prompt, but both are just
  tokens in the context. A user can try to override the rules (prompt
  injection), so the system instructions are not a security boundary.
- **Other roles.** The conversation also holds `assistant` messages (the
  LLM's replies) and tool results: `tool` messages in Chat Completions and
  `function_call_output` items in the Responses API.

## Neural Networks

An LLM is a neural network: a function with billions of numbers, called
parameters or weights, that turns input numbers into output numbers.
Training sets the weights; using the model (inference) only runs the
function. This app only runs inference, through the LLM provider's API.

### One Neuron

A neuron multiplies each input by a weight, adds the results and a bias,
then applies an activation function `f`:

```text
y = f(w1*x1 + w2*x2 + ... + wn*xn + b) = f(w · x + b)
```

- `x` is the input vector and `w` the weight vector.
- `w · x` is the dot product: multiply matching entries, then add them.
- `b` is the bias, a single number.
- `f` adds non-linearity. Common choices are ReLU, `f(z) = max(0, z)`,
  and GELU, a smooth version of ReLU.

Without `f`, stacking layers would still be one linear function, however
many layers there were.

### A Layer Is a Matrix Multiplication

A layer is many neurons reading the same input. Their weight vectors form
the rows of a weight matrix `W`, so the whole layer is:

```text
y = f(W x + b)
```

Example with 2 inputs and 2 neurons:

```text
W = | 1  2 |   x = | 3 |   b = | 1 |
    | 0 -1 |       | 4 |       | 2 |

W x     = | 1*3 + 2*4    |  = | 11 |
          | 0*3 + (-1)*4 |    | -4 |

W x + b = | 12 |   ReLU ->  | 12 |
          | -2 |            |  0 |
```

A network chains layers, each feeding the next:

```text
output = f3(W3 f2(W2 f1(W1 x + b1) + b2) + b3)
```

### The Math Operations

| Operation | What it does | Where it is used |
|---|---|---|
| Dot product | Multiply pairs, then sum | Each neuron; attention scores |
| Matrix-vector product | Many dot products at once | Each layer, one token |
| Matrix-matrix product | Many vectors at once | Layers over all tokens |
| Vector addition | Add matching entries | Bias; residual connections |
| Element-wise product | Multiply matching entries | Feed-forward gating |
| Activation | `max`, `exp`, `tanh` per entry | After most layers |
| Softmax | `exp`, sum, then divide | Attention; next-token odds |
| Normalization | Mean, variance, square root | Before each block |
| Transpose | Swap rows and columns | Attention (`K` to `Kᵀ`) |

Softmax turns any list of numbers into probabilities that sum to 1:

```text
softmax(z)_i = exp(z_i) / (exp(z_1) + exp(z_2) + ... + exp(z_n))
```

Nearly all the work is multiply-then-add, so hardware is built around one
fused step: `acc = acc + a * b`, the multiply-accumulate.

### How an LLM Uses These Operations

LLMs are transformers. To produce each new token, the model runs:

1. **Embedding.** Each input token is replaced by a learned vector, a row
   looked up from an embedding matrix.
2. **Attention.** Each token's vector is multiplied by three weight
   matrices to get query, key, and value vectors:

   ```text
   Q = X W_Q    K = X W_K    V = X W_V
   Attention(Q, K, V) = softmax(Q Kᵀ / √d) V
   ```

   `Q Kᵀ` scores how much each token relates to every other token, `√d`
   (from the vector length `d`) keeps the scores in a stable range, and
   the softmax weights are used to mix the value vectors.
3. **Feed-forward.** Each token's vector goes through two or three layers,
   such as `W2 f(W1 x)`.
4. **Residual and normalization.** Each block's input is added to its
   output, and the vectors are normalized. Steps 2 to 4 repeat for every
   layer, often 30 to 100 or more.
5. **Output.** The final vector is multiplied by an output matrix, giving
   one score (a logit) per vocabulary token. Softmax turns the scores into
   probabilities, and one token is picked. The loop then repeats with that
   token added.

### Linear or Exponential?

Neither. An LLM is a non-linear function built mostly from linear pieces,
with a few other function types placed between them:

| Function type | Formula | Where it is used |
|---|---|---|
| Linear (affine) | `W x + b` | Every layer; attention projections |
| Piecewise linear | ReLU: `max(0, z)` | Activation in some models |
| Exponential | `exp(z)` | Softmax |
| Sigmoid | `σ(z) = 1 / (1 + exp(-z))` | Inside SiLU and SwiGLU |
| Gaussian-based | GELU: `z Φ(z)` | Activation in some models |
| Quadratic | `Q Kᵀ` | Attention scores |
| Square root, division | `x / sqrt(mean(x²) + ε)` | RMSNorm normalization |

`Φ` is the cumulative distribution function of the standard normal
distribution, and `ε` is a tiny constant that avoids dividing by zero.

- **Matrix products do almost all the work.** Most multiplications
  happen in `W x + b`. Attention's `Q Kᵀ` and its product with `V` do most
  of the rest, a share that grows with the length of the input.
- **Non-linear parts are cheap but essential.** They act on one entry at a
  time. Without them, all the layers would collapse into one matrix.
- **Attention is quadratic in its input.** `Q` and `K` are both linear in
  the input `X`, so their product `Q Kᵀ` is quadratic.
- **Exponentials appear only inside other functions,** such as softmax
  and sigmoid. The network as a whole is not exponential.

The activation choice varies by model. Many recent LLMs use SwiGLU in
their feed-forward layers, where `⊙` is the element-wise product:

```text
SiLU(z) = z σ(z)
FFN(x)  = (SiLU(x W1) ⊙ (x W3)) W2
```

Stacking many such layers gives a highly non-linear function. That is
what lets the network represent complex patterns, since any stack of
purely linear layers could only draw straight-line relationships.

### Scale

Each parameter takes part in about one multiply and one add per token, so
generating one token costs about `2 x parameters` operations. The model in
`config.yaml`, `nemotron-3-super-120b-a12b`, has 120 billion parameters,
of which the name says about 12 billion are active per token. That is
roughly 24 billion operations for every token generated. GPUs run these
because they perform thousands of multiply-accumulates in parallel.

### Training

Training runs the network, measures its error with a loss function, and
uses backpropagation (the chain rule of calculus, computed with more
matrix products) to find how each weight affects the error. Gradient
descent then nudges every weight to reduce it:

```text
w = w - learning_rate * (∂loss / ∂w)
```

### Why This App Uses a Calculator

An LLM does not compute `4 + 4 * 3`. It predicts the most likely next
token from patterns in its training data, which is often right for simple
arithmetic but unreliable for longer numbers. So the system instructions
tell the model not to do arithmetic itself, and it calls the calculator
MCP tools instead, which compute exact results.
