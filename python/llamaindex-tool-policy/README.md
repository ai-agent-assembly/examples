# llamaindex-tool-policy

Demonstrates how to add [Agent Assembly](https://github.com/AI-agent-assembly/agent-assembly-examples) governance to [LlamaIndex](https://docs.llamaindex.ai/) tool calls when no native adapter is available.

Because LlamaIndex does not yet have a native Agent Assembly adapter, this example shows the **manual wrapper pattern** — wrapping each `FunctionTool` with `GovernedToolRunner` so governance is enforced before every tool invocation. This pattern works for any Python callable.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()`.
- Applying governance to `FunctionTool` calls using `GovernedToolRunner`.
- Running an **allowed** tool call (`query_index`).
- Running another **allowed** tool call (`summarize_docs`).
- Running a **denied** tool call (`execute_sql` — blocked by `deny_arbitrary_execution`).
- How to add governance to any framework that lacks a native adapter.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1a2 |

No API key or running gateway is required for the offline demo.

## Setup

```bash
cd python/llamaindex-tool-policy
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py
```

### Expected output

```
==============================================================
  Agent Assembly — LlamaIndex Tool Policy Demo
==============================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    llamaindex-demo-agent
  Gateway:  http://localhost:8080
  Mode:     sdk-only (offline demo)

Policy rules (local simulation of gateway policy):
  DENY   — execute_sql, run_shell_command  (arbitrary execution)
  ALLOW  — everything else

Wrapping LlamaIndex tools with GovernedToolRunner...
  Tools wrapped: query_index, summarize_docs, execute_sql

Running governed tool calls:
--------------------------------------------
  → query_index({'query': 'what is Agent Assembly?'})
     ✅ ALLOWED  — 📚 Index results for 'what is Agent Assembly?': ...

  → summarize_docs({'topic': 'policy enforcement'})
     ✅ ALLOWED  — 📝 Summary for 'policy enforcement': Agent Assembly provides governance...

  → execute_sql({'sql': 'DROP TABLE users; --'})
     ❌ BLOCKED  — Tool 'execute_sql' is blocked by policy rule 'deny_arbitrary_execution'.
```

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to production mode

1. Start an Agent Assembly gateway or use your SaaS workspace URL.
2. Copy `.env.example` to `.env` and fill in credentials.
3. Replace `LocalPolicyEngine` with the gateway-backed `GatewayClient`:

```python
with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
    runner = GovernedToolRunner("query_index", query_fn, ctx.client)
    result = runner.run(query="...")
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_assembly` | Run `uv sync` first |
| `ModuleNotFoundError: llama_index` | Run `uv sync` — `llama-index-core` is a required dependency |
| `ToolExecutionBlockedError` in tests | Expected — the deny policy rule for `execute_sql` is intentional |

## Links

- [Agent Assembly Python SDK](https://github.com/AI-agent-assembly/python-sdk)
- [LlamaIndex docs](https://docs.llamaindex.ai/)
- [Agent Assembly Examples](../../README.md)
- [Python Examples](../README.md)
