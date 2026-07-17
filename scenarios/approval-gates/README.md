# Approval Gates Scenario

This scenario demonstrates how Agent Assembly's `approval_required` policy action
intercepts a risky tool call, pauses execution, waits for an approver, and only
then allows the tool to run.

## What you will see

| Step | Tool | Outcome |
|---|---|---|
| 1 | `get_balance` | Executes immediately — policy says `allow` |
| 2 | `transfer_funds` | Pauses — policy says `approval_required`; mock approver auto-approves; tool executes |

## Policy walkthrough

```yaml
# scenarios/approval-gates/policy.yaml
rules:
  - tool: get_balance
    action: allow
    reason: "Read-only balance check is permitted"

  - tool: transfer_funds
    action: approval_required
    reason: "Fund transfers require human approval before execution"

default_action: deny
default_reason: "Unlisted tools are denied by default (fail-closed policy)"
```

`approval_required` is a third policy action alongside `allow` and `deny`.
It means: *pause the tool call, submit an approval request, and resume only
if the request is granted*. If the approver rejects (or no approver responds),
`ToolExecutionBlockedError` is raised and the tool body never runs.

## How the approval flow works

```
1. Governed wrapper calls on_tool_start()
         ↓
2. Policy engine returns status="pending"
         ↓
3. SDK calls interceptor.wait_for_tool_approval()
         ↓
4. Approval client submits request, waits for decision
         ↓
5. Approver approves → SDK allows tool to execute
   Approver rejects → SDK raises ToolExecutionBlockedError
```

The `governed()` helper in `src/approval.py` wires all of this together using
the standard `AssemblyCallbackHandler` from the Agent Assembly SDK.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.12 |
| uv | latest |
| `agent-assembly` SDK | ≥ 0.0.1rc6 |
| PyYAML | ≥ 6.0 |

Node.js implementation:

| Requirement | Version |
|---|---|
| Node.js | ≥ 20 |
| pnpm | latest |
| `@agent-assembly/sdk` | ≥ 0.0.1-rc.6 |

## Run: Python

```bash
cd scenarios/approval-gates/python
uv sync --extra dev
uv run python src/main.py
```

To run the tests:

```bash
uv run pytest tests/ -v
```

## Run: Node.js

```bash
cd scenarios/approval-gates/node
pnpm install
pnpm start
```

To run the tests:

```bash
pnpm test
```

## Expected output

```
==============================================================
  Agent Assembly — Approval Gates Scenario
==============================================================

Policy loaded from policy.yaml  (2 rules, default: deny)
  ALLOW              get_balance    — Read-only balance check is permitted
  APPROVAL_REQUIRED  transfer_funds — Fund transfers require human approval before execution

Running governed tool calls:
--------------------------------------------
  → get_balance(account_id='acc-001')
     ✅ EXECUTED — $12,450.00

  → transfer_funds(from_account='acc-001', to_account='acc-002', amount=500.0)
     ⏳ PENDING  — approval required for 'transfer_funds'
     ✅ APPROVED — MockApprovalClient auto-approved (request_id='mock-req-001')
     ✅ EXECUTED — Transferred $500.00 from acc-001 to acc-002

2 tool calls: 2 succeeded (1 immediate, 1 via approval).
```

## What to copy into a real application

1. **`policy.yaml` with `approval_required`** — use the same YAML schema; the
   gateway evaluates it and returns `pending` decisions to the SDK automatically.

2. **A real approval client** — replace `MockApprovalClient` with a class that
   sends a Slack message, writes to a database, or calls your ticketing system
   and blocks until the operator responds.

3. **Webhook or API integration** — the real approval client needs a callback
   endpoint so the operator's Approve/Reject action unblocks the waiting SDK call.

## What is intentionally simplified

- **Mock auto-approver** — `MockApprovalClient` approves every request immediately
  with a 50 ms simulated delay; a real approver blocks for minutes or hours.

- **No timeout or escalation** — the demo waits indefinitely; production systems
  need a timeout after which the request is auto-rejected or escalated.

- **No audit trail** — the demo prints to stdout; production deployments route
  approval decisions through the Agent Assembly gateway audit log.

---

← [Back to scenarios](../README.md)
