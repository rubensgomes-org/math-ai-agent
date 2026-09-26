# LLM Models

This page provides general information about the LLM models used on this
project.

## NVIDIA

NVIDIA's catalog is public — `GET https://integrate.api.nvidia.com/v1/models`
lists every served model id without authentication. Get a key from
<https://build.nvidia.com> (free developer account); keys start with `nvapi-`.

## OpenRouter Miscellaneous Models

Two provider gotchas worth knowing. OpenRouter's `:free` model variants (for
example `nvidia/nemotron-3-super-120b-a12b:free`) are capped at 50 requests per
day, after which every call fails with `429 free-models-per-day`; the `:free`
suffix is OpenRouter slug syntax and is not a valid model id anywhere else.
NVIDIA serves the same model under the bare id at a higher free rate limit, but
responds noticeably slower per turn.

Any OpenAI-compatible endpoint works, since the app talks to it through the
OpenAI SDK. Which SDK surface it uses is controlled by `llm.api_style`.

## OpenAI: Responses vs Chat Completions API

Several providers label `/v1/responses` beta or
experimental — OpenRouter's is beta and strictly stateless (it rejects
`store: true` and `previous_response_id` with HTTP 400), and NVIDIA's is marked
experimental. Both work with this app, as does Ollama v0.13.3+. The Responses
agent loop replays every output Item back as input on each turn rather than
relying on server-side state, which is what keeps it portable across all of
them and unchanged against `https://api.openai.com/v1`. Not every model in a
provider's catalog is necessarily served over its Responses endpoint — if a
model 404s or 400s under `api_style: "responses"`, either pick a model that
supports it or set `api_style: "chat"`.

## Server-Side Storage

Both clients send `store=False` on every request, so
neither API retains the conversation. This matters most on the Responses API,
which stores by default; Chat Completions already defaults to not storing, but
the flag is sent there too because OpenAI accounts carry a separate
data-retention setting that can enable storage when the parameter is omitted.
Note this controls the API's own storage, not org-level dashboard logging.

See [OLLAMA.md](OLLAMA.md) for running models locally.
