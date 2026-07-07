# langchain-basic-agent

Demonstrates how to integrate [Agent Assembly](https://github.com/ai-agent-assembly/agent-assembly-examples) with [LangChain](https://python.langchain.com/) to enforce governance policy on tool calls before execution.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()`.
- Wrapping LangChain tools with `AssemblyCallbackHandler` + a governance interceptor.
- Running an **allowed** tool call (`get_weather`).
- Running a **denied** tool call (`delete_files` — blocked by a policy rule).
- Running a **pending** tool call (`send_email` — requires human approval; auto-denied in offline mode).
- How `ToolExecutionBlockedError` is raised when a tool is blocked.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1rc3 |

No running Agent Assembly gateway is required for the offline demo.

## Setup

```bash
cd python/langchain-basic-agent
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py
```

### Expected output

```
==============================================================
  Agent Assembly — LangChain Basic Agent Demo
==============================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    langchain-demo-agent
  Gateway:  http://localhost:8080
  Mode:     sdk-only (offline demo)

Policy rules (local simulation of gateway policy):
  DENY    — delete_files, write_file  (destructive operations)
  PENDING — send_email                (requires human approval)
  ALLOW   — everything else

Running governed tool calls:
--------------------------------------------
  → get_weather({"city": "London"})
     ✅ ALLOWED  — 🌤  Weather in {"city": "London"}: 22°C, partly cloudy (mock response)

  → delete_files({"path": "/etc/passwd"})
     ❌ BLOCKED  — Tool 'delete_files' is blocked by policy rule 'deny_destructive_operations'.

  → send_email({"to": "all@company.com", "subject": "Hello", "body": "World"})
     ❌ BLOCKED  — Tool 'send_email' requires approval, but no approver is available in offline mode.

Assembly context shut down.
```

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to production mode

1. Start an Agent Assembly gateway or use your SaaS workspace URL.
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Run with gateway environment variables:

```bash
AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \
AGENT_ASSEMBLY_API_KEY=your-key \
uv run python src/main.py
```

In production, remove the `mode="sdk-only"` argument from `init_assembly()` and replace `LocalPolicyEngine` with the gateway-backed interceptor. The SDK will enforce policy rules configured in the gateway automatically.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_assembly` | Run `uv sync` first |
| `ModuleNotFoundError: langchain_core` | Run `uv sync` — `langchain-core` is a required dependency |
| `ToolExecutionBlockedError` in tests | Expected — the deny/pending policy rules are intentional |

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [Agent Assembly Examples](../../README.md)
- [Python Examples](../README.md)
