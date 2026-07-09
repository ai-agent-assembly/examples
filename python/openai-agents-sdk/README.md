# openai-agents-sdk

Demonstrates how to integrate [Agent Assembly](https://github.com/ai-agent-assembly/examples) with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) to enforce governance policy — including approval gates — on tool calls before execution.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()`.
- Enforcing a governance policy using `AssemblyCallbackHandler` + a policy interceptor.
- Running an **allowed** tool call (`search_documents`).
- Running a tool that requires **human approval** (`send_message_to_user` — auto-denied offline).
- Running a **denied** tool call (`delete_record` — blocked by a policy rule).
- How the `OpenAIAgentsPatch` intercepts `FunctionTool.__call__` at the framework level.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1rc3 |

No `OPENAI_API_KEY` is required for the offline demo.

## Setup

```bash
cd python/openai-agents-sdk
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py
```

### Expected output

```
==============================================================
  Agent Assembly — OpenAI Agents SDK Demo
==============================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    openai-agents-demo
  Gateway:  http://localhost:8080
  Mode:     sdk-only (offline demo)

Policy rules (local simulation of gateway policy):
  DENY      — delete_record, drop_table  (destructive data ops)
  APPROVAL  — send_message_to_user, trigger_payment
  ALLOW     — everything else

Running governed tool calls:
--------------------------------------------
  → search_documents({"query": "agent governance best practices"})
     ✅ ALLOWED  — 📄 Search results for 'agent governance best practices': ...

  → send_message_to_user({"user_id": "u-001", "message": "Your report is ready."})
     ❌ BLOCKED  — Tool 'send_message_to_user' requires approval, but no approver is available in offline mode.

  → delete_record({"record_id": "rec-7829"})
     ❌ BLOCKED  — Tool 'delete_record' is permanently blocked by policy rule 'deny_destructive_data_ops'.
```

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to production mode (with real OpenAI API key)

1. Start an Agent Assembly gateway or use your SaaS workspace URL.
2. Copy `.env.example` to `.env` and fill in your credentials.
3. Run with environment variables:

```bash
OPENAI_API_KEY=sk-... \
AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \
AGENT_ASSEMBLY_API_KEY=your-key \
uv run python src/main.py
```

When an `OPENAI_API_KEY` is set, you can extend `main.py` to create a real `openai.agents.Agent` with your `FunctionTool` instances. Agent Assembly's `OpenAIAgentsPatch` intercepts every tool call automatically once `init_assembly()` has run.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_assembly` | Run `uv sync` first |
| `ModuleNotFoundError: openai` | Run `uv sync` — `openai-agents` is a required dependency |
| `ToolExecutionBlockedError` in tests | Expected — the deny/approval policy rules are intentional |

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)
- [Agent Assembly Examples](../../README.md)
- [Python Examples](../README.md)
