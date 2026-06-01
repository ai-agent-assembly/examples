# Policy Enforcement Scenario

Demonstrates how a shared `policy.yaml` file drives allow/deny decisions for every
tool call made by an agent — with no gateway, no API key, and no AI framework required.

## What you will see

- A `policy.yaml` file that declares explicit `allow` / `deny` rules per tool name.
- A `LocalPolicyEngine` that loads the file and evaluates each tool call at runtime.
- Two **allowed** calls (`read_config`, `list_agents`).
- Two **denied** calls (`delete_agent`, `send_email`) — the function body never executes.
- A final summary line: `4 tool calls: 2 allowed, 2 denied.`

## Policy walkthrough

```yaml
version: "1"
agent_id: policy-enforcement-demo

rules:
  - tool: read_config
    action: allow
    reason: "Read-only configuration access is permitted"

  - tool: list_agents
    action: allow
    reason: "Read-only agent listing is permitted"

  - tool: delete_agent
    action: deny
    reason: "Destructive operations are blocked by policy (rule: no_destructive_ops)"

  - tool: send_email
    action: deny
    reason: "Network egress tools are blocked by default (rule: no_network_egress)"

default_action: deny
default_reason: "Unlisted tools are denied by default (fail-closed policy)"
```

Rules are evaluated top-to-bottom.  Any tool not listed falls through to the
`default_action: deny` — a fail-closed policy that blocks everything unknown.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Node.js | >= 20 |
| [pnpm](https://pnpm.io) | latest |
| Go | >= 1.22 |
| Agent Assembly Python SDK | >= 0.0.1a2 |

No API key or gateway is required — this scenario runs fully offline.

## Run: Python

```bash
cd scenarios/policy-enforcement/python
uv sync
uv run python src/main.py
```

### Run tests

```bash
uv run pytest tests/ -v
```

## Run: Node.js

```bash
# Coming soon — see scenarios/README.md for the planned structure
cd scenarios/policy-enforcement/node
pnpm install
pnpm start
```

## Run: Go

```bash
# Coming soon — see scenarios/README.md for the planned structure
cd scenarios/policy-enforcement/go
go run ./...
```

## Expected output

```
==============================================================
  Agent Assembly — Policy Enforcement Scenario
==============================================================

Policy loaded from policy.yaml  (4 rules, default: deny)
  ALLOW  read_config    — Read-only configuration access is permitted
  ALLOW  list_agents    — Read-only agent listing is permitted
  DENY   delete_agent   — Destructive operations are blocked by policy (rule: no_destructive_ops)
  DENY   send_email     — Network egress tools are blocked by default (rule: no_network_egress)

Running governed tool calls:
--------------------------------------------
  → read_config(key='database.host')
     ✅ ALLOWED  — localhost:5432

  → list_agents()
     ✅ ALLOWED  — ['agent-001', 'agent-002', 'agent-003']

  → delete_agent(agent_id='agent-001')
     ❌ DENIED   — Destructive operations are blocked by policy (rule: no_destructive_ops)

  → send_email(to='admin@example.com', subject='Hello', body='Test message')
     ❌ DENIED   — Network egress tools are blocked by default (rule: no_network_egress)

4 tool calls: 2 allowed, 2 denied.
```

## What to copy into a real application

1. **`policy.yaml`** — copy to your project root and extend the `rules` list with your
   own tools and actions.  The `default_action: deny` keeps the policy fail-closed.

2. **`governed()` wrapper** — the `governed(tool_name, fn, policy)` helper in
   `python/src/policy.py` is the minimal pattern for applying governance to any
   plain Python function.  Copy it into your project and adapt `LocalPolicyEngine`
   to accept your tool names.

3. **`LocalPolicyEngine` → gateway swap** — when you are ready to connect to a real
   Agent Assembly gateway, replace `LocalPolicyEngine` with the gateway-backed client:

   ```python
   from agent_assembly import init_assembly

   with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
       tools = {name: governed(name, fn, ctx.client) for name, fn in raw_fns.items()}
   ```

## What is intentionally simplified

- **Local file, not a gateway** — `LocalPolicyEngine` reads `policy.yaml` from disk.
  A production deployment evaluates rules in the Agent Assembly gateway, which supports
  dynamic rule updates and team-scoped policies.

- **No approval or audit trail** — this scenario shows allow/deny only.  See the
  `approval-gates/` and `audit-trace/` scenarios for those capabilities.

- **Mock data** — `read_config` and `list_agents` return hard-coded values so the
  demo runs without any external service.

## Back to scenarios

[← Scenario Examples](../README.md)
