# langchain-research-agent

A richer ReAct variant of [`langchain-basic-agent`](../langchain-basic-agent). It
shows how [Agent Assembly](https://github.com/ai-agent-assembly/examples)
governs a [LangChain](https://python.langchain.com/) **research agent** that
reasons through a question using a web-search tool and a calculator tool — under
a single *balanced* governance policy.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()` in `sdk-only` mode.
- A ReAct-style research trajectory over two tools: `web_search` and `calculator`.
- A **balanced policy** that bundles four controls at once:
  - **Network allowlist** — outbound egress is only allowed to `*.openai.com`.
  - **Daily budget** — tool calls are metered against a `$1.00 / day` cap.
  - **Tool-call logging** — every governed call is recorded as an audit event.
  - **Credential-leak block** — any tool input carrying a secret is denied.
- A credential-leak demo that uses a **SAFE, FAKE** key (`sk-FAKE...`) — never a
  real secret — to show the leak rule firing.
- `--mock` mode: the whole demo runs offline with no API keys, so CI can run it.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1b2 |

No running Agent Assembly gateway and no API keys are required for the mock demo.

## Setup

```bash
cd python/langchain-research-agent
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py --mock
```

`--mock` replays a scripted ReAct trajectory offline. The example also auto-falls
back to mock mode whenever `OPENAI_API_KEY` is unset.

### Expected governance output

```
================================================================
  Agent Assembly — LangChain ReAct Research Agent
================================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    langchain-research-agent
  Gateway:  http://localhost:8080
  Mode:     sdk-only (mock (offline))

Balanced policy (local simulation of gateway policy):
  ALLOWLIST — outbound egress to *.openai.com, openai.com
  BUDGET    — $1.00 / day, metered per tool call
  LOG       — every tool call recorded as an audit event
  BLOCK     — any tool input that leaks a credential

Running ReAct research trajectory:
----------------------------------------------
  → web_search({"query": "speed of light"})
     ✅ ALLOWED  — The speed of light in vacuum is 299792458 metres per second.

  → web_search({"query": "population of France"})
     ✅ ALLOWED  — France has a population of approximately 68000000 people.

  → calculator({"expression": "299792458 / 68000000"})
     ✅ ALLOWED  — 299792458 / 68000000 = 4.40871

  → web_search({"query": "fetch https://evil-exfil.example.com/leak"})
     ❌ BLOCKED  — Tool 'web_search' attempted egress to 'evil-exfil.example.com', which is not on the network allowlist (*.openai.com).

Credential-leak demo (SAFE FAKE key):
----------------------------------------------
  → web_search({"query": "summarize using api_key=sk-FAKE0000DEMO0000NOTAREALKEY0000"})
     ❌ BLOCKED  — Tool 'web_search' input contains a credential and is blocked by policy rule 'block_credential_leak'.

Governance events recorded this run:
----------------------------------------------
  ✅ web_search   allow — allowed (charged $0.02; spent=$0.02 / limit=$1.00 (2%))
  ✅ web_search   allow — allowed (charged $0.02; spent=$0.04 / limit=$1.00 (4%))
  ✅ calculator   allow — allowed (charged $0.00; spent=$0.04 / limit=$1.00 (4%))
  ❌ web_search   deny  — Tool 'web_search' attempted egress to 'evil-exfil.example.com', which is not on the network allowlist (*.openai.com).
  ❌ web_search   deny  — Tool 'web_search' input contains a credential and is blocked by policy rule 'block_credential_leak'.

Final budget: spent=$0.04 / limit=$1.00 (4%)

Assembly context shut down.
```

### How to read the governance events

| Event | Governance control | Outcome |
|---|---|---|
| `web_search("speed of light")` | tool-call capture + budget | **ALLOWED**, charged `$0.02` |
| `web_search("population of France")` | tool-call capture + budget | **ALLOWED**, charged `$0.02` |
| `calculator(...)` | tool-call capture + budget | **ALLOWED**, `$0.00` (local compute) |
| `web_search(... evil-exfil.example.com ...)` | network allowlist | **BLOCKED** — host not on `*.openai.com` |
| `web_search(... api_key=sk-FAKE... )` | credential-leak block | **BLOCKED** — secret detected in input |

The final block replays the full audit trail and the running budget total — the
governance evidence a real gateway would persist server-side.

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to production mode

1. Start an Agent Assembly gateway (or use your SaaS workspace URL).
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Configure the balanced policy (allowlist / budget / redaction) in the gateway.
4. Run without `--mock` and with a real LLM provider key:

```bash
AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \
AGENT_ASSEMBLY_API_KEY=your-key \
OPENAI_API_KEY=sk-your-real-key \
uv run python src/main.py
```

In production, replace `BalancedPolicyEngine` with the gateway-backed interceptor;
the SDK enforces the policy rules configured in the gateway automatically.

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [Python Examples](../README.md)
