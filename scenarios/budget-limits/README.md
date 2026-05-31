# Budget Limits Scenario

Demonstrates how Agent Assembly enforces **budget guardrails** on AI agent tool
calls — limiting how much cost an agent can accumulate in a session before
further calls are denied.

## Concept

Each tool call an AI agent makes carries a cost (token usage, API charges, or a
custom unit). Agent Assembly tracks cumulative spend per session and enforces the
ceiling defined in the budget policy. When the ceiling is reached, further calls
are denied immediately with a clear explanation.

```
Agent  →  call_tool("generate_report")  →  [Agent Assembly runtime]
                                                ↓  budget check
                                           spent=$0.35 + cost=$0.25 = $0.60
                                                ↓  exceeds limit $0.50
                                           BudgetExceeded raised  →  Agent
```

## What this example shows

| Tool call           | Cost   | Running total | Decision        |
|---------------------|--------|---------------|-----------------|
| `web_search`        | $0.05  | $0.05         | ✓ allow         |
| `query_database`    | $0.10  | $0.15         | ✓ allow         |
| `call_external_api` | $0.20  | $0.35         | ✓ allow         |
| `web_search`        | $0.05  | $0.40         | ✓ allow         |
| `generate_report`   | $0.25  | —             | ✗ deny — $0.25 > $0.10 remaining |
| `call_external_api` | $0.20  | —             | ✗ deny — $0.20 > $0.10 remaining |

## Policy

Budget limits are defined in [`policy.yaml`](policy.yaml). The key fields are:

```yaml
budget:
  max_cost: 0.50        # session ceiling
  window: session       # tracking scope
  on_exceed: deny       # action when limit is hit

tool_costs:
  web_search: 0.05
  query_database: 0.10
  call_external_api: 0.20
  generate_report: 0.25
```

In production, this file is uploaded to the Agent Assembly gateway via:

```bash
aasm policy upload policy.yaml --agent <agent-id>
```

## Prerequisites

Choose one language:

- **Python** — Python 3.9+ (no additional packages required)
- **Node.js** — Node.js 18+ (no additional packages required)

No API keys or external services needed. Both examples run fully offline.

## Run

### Python

```bash
cd python
python agent.py
```

### Node.js

```bash
cd node
node agent.js
```

## Expected output

See [`expected-output.txt`](expected-output.txt) for the reference output.

## Troubleshooting

**Budget never triggers?**  
Verify the `BUDGET_LIMIT` constant in `agent.py` (or `agent.js`) matches the
`max_cost` in `policy.yaml`. The offline example uses the constant directly.

**Want to test a different limit?**  
Change the `max_cost` in `policy.yaml` and update the matching constant at the
top of the agent script.

## Notes on production usage

- In production, the budget ceiling and per-tool costs are fetched from the
  Agent Assembly gateway — not from a local constant.
- The `window` field controls scope: `session`, `daily`, or `monthly`.
- When `on_exceed` is `throttle` instead of `deny`, calls are queued until the
  window resets rather than rejected outright.
- Budget events are included in the audit stream; see the **audit-trace**
  scenario for how to inspect them.
