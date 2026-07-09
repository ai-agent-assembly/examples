# haystack-tool-policy

Demonstrates [Agent Assembly](https://github.com/ai-agent-assembly/examples) governance over a real [Haystack](https://haystack.deepset.ai/) agent using the SDK's **native Haystack adapter**.

Haystack has a native adapter: `HaystackPatch` hooks `haystack.tools.Tool.invoke` — the single execution chokepoint Haystack 2.x uses for every tool, including the agentic `Agent` → `ToolInvoker` tool-call loop. This example governs three real `haystack.tools.Tool` instances by driving them through a genuine `ToolInvoker` (the component a Haystack `Agent` uses to execute a model-chosen tool call), so a denied tool is short-circuited **before its body runs** — real governance, not a no-op.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()` (which auto-detects Haystack).
- Installing the native Haystack adapter (`HaystackPatch`) against a local policy.
- Running real `haystack.tools.Tool` calls through a real `ToolInvoker`.
- An **allowed** tool call (`query_index`) — the tool body executes.
- Another **allowed** tool call (`summarize_docs`).
- A **denied** tool call (`execute_sql` — blocked by `deny_arbitrary_execution`); its underlying function never runs.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1rc3 |
| Haystack | >= 2.0.0, < 3.0 |

No API key or running gateway is required for the offline demo — the tools are driven through a `ToolInvoker` with a hand-built `ToolCall`, so no LLM is involved.

## Setup

```bash
cd python/haystack-tool-policy
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py
```

### Expected output

```
==============================================================
  Agent Assembly — Haystack Tool Policy Demo
==============================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    haystack-demo-agent
  Gateway:  http://localhost:8080
  Mode:     sdk-only (offline demo)

Policy rules (local simulation of gateway policy):
  DENY   — execute_sql, run_shell_command  (arbitrary execution)
  ALLOW  — everything else

Installing the native Haystack adapter against the demo policy...
  Adapter installed: True

Running real Haystack tools through a ToolInvoker:
--------------------------------------------
  → query_index({'query': 'what is Agent Assembly?'})
     ✅ ALLOWED  — Index results for 'what is Agent Assembly?': [chunk-12, chunk-44, chunk-07] (mock)

  → summarize_docs({'topic': 'policy enforcement'})
     ✅ ALLOWED  — Summary for 'policy enforcement': Agent Assembly provides governance... (mock)

  → execute_sql({'sql': 'DROP TABLE users; --'})
     ❌ BLOCKED  — [BLOCKED by governance policy] Tool 'execute_sql' is blocked by policy rule 'deny_arbitrary_execution'...

Tool bodies that actually executed: ['query_index', 'summarize_docs']
```

`execute_sql` is absent from the executed list — the deny short-circuited it before the tool ran.

## Run tests

```bash
uv run pytest tests/ -v
```

## How the offline demo wires the policy

`init_assembly()` auto-detects Haystack and patches `Tool.invoke` for you. In offline `sdk-only` mode it wires a no-op interceptor (there is no live gateway to answer policy), so this demo reverts that and re-installs the same native adapter against a `LocalPolicyEngine` to make a real allow/deny visible without a gateway.

In production you point `init_assembly()` at a gateway and let its auto-detected adapter enforce real policy — no manual re-install needed:

```python
with init_assembly(gateway_url="https://your-workspace", api_key="...", agent_id="my-agent") as ctx:
    # Haystack tools are governed automatically from here.
    ...
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_assembly` | Run `uv sync` first |
| `ModuleNotFoundError: haystack` | Run `uv sync` — `haystack-ai` is a required dependency |
| `execute_sql` shows ALLOWED | Make sure the demo policy is installed *after* `init_assembly()` (it reverts the auto-applied no-op patch); see `src/main.py` |

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [Haystack docs](https://haystack.deepset.ai/)
- [Agent Assembly Examples](../../README.md)
- [Python Examples](../README.md)
