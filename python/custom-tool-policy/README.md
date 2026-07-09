# custom-tool-policy

The simplest Agent Assembly integration — no AI framework required.

Demonstrates how to add [Agent Assembly](https://github.com/ai-agent-assembly/examples) governance to plain Python functions using the minimal `governed()` wrapper helper.

## What this example demonstrates

- Initializing Agent Assembly with `init_assembly()`.
- Wrapping any Python function with governance using `governed()`.
- Two **allowed** tool calls (`compute_sum`, `fetch_stock_price`).
- Two **denied** tool calls (`send_http_request`, `write_to_disk` — blocked by policy).
- That the wrapped function body **never executes** when governance denies it.
- The `governed()` pattern as the building block for the `GovernedToolRunner` shown in the `llamaindex-tool-policy` example.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1rc3 |

No API key, no gateway, and no AI framework are required.

## Setup

```bash
cd python/custom-tool-policy
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py
```

### Expected output

```
==============================================================
  Agent Assembly — Custom Tool Policy Demo
  (no AI framework required)
==============================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    custom-tool-demo-agent
  Gateway:  http://localhost:8080
  Mode:     sdk-only (offline demo)

Policy rules (local simulation of gateway policy):
  DENY   — send_http_request, write_to_disk  (network / disk writes)
  ALLOW  — everything else

Running governed tool calls:
--------------------------------------------
  → compute_sum({'a': 12.5, 'b': 7.3})
     ✅ ALLOWED  — 19.8

  → fetch_stock_price({'ticker': 'AAPL'})
     ✅ ALLOWED  — $211.30 (mock)

  → send_http_request({'url': 'https://example.com/data', 'method': 'POST'})
     ❌ BLOCKED  — Tool 'send_http_request' is blocked by policy rule 'deny_network_and_disk_writes'.

  → write_to_disk({'path': '/etc/cron.d/evil', 'content': 'rm -rf /'})
     ❌ BLOCKED  — Tool 'write_to_disk' is blocked by policy rule 'deny_network_and_disk_writes'.
```

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to production mode

Replace `LocalPolicyEngine` with `ctx.client` (the gateway-backed interceptor):

```python
from agent_assembly import init_assembly
from agent_assembly.adapters.langchain import AssemblyCallbackHandler

with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
    from src.policy import governed
    tools = {
        "compute_sum": governed("compute_sum", compute_sum, ctx.client),
    }
    result = tools["compute_sum"](a=1, b=2)
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: agent_assembly` | Run `uv sync` first |
| `ToolExecutionBlockedError` in tests | Expected — the deny rules for `send_http_request` and `write_to_disk` are intentional |

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [Agent Assembly Examples](../../README.md)
- [Python Examples](../README.md)
