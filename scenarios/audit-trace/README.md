# Audit / Trace Scenario

Demonstrates how Agent Assembly records **audit events** for every governed tool
call an AI agent makes — whether the call was allowed, denied, or held for human
approval.

## Concept

When an AI agent calls a tool through Agent Assembly, the runtime evaluates the
call against a policy and writes an **audit record** before the call proceeds (or
is blocked). The audit stream gives operators full visibility into what the agent
tried to do and why each decision was made.

```
Agent  →  call_tool("delete_file")  →  [Agent Assembly runtime]
                                              ↓  policy check
                                         Decision: DENY
                                              ↓
                                         Audit record written
                                              ↓
                                         PermissionError raised  →  Agent
```

## What this example shows

| Tool call      | Decision           | Demonstrates                                        |
|----------------|--------------------|-----------------------------------------------------|
| `read_file`    | `allow`            | Normal allowed call — audit record written          |
| `delete_file`  | `deny`             | Blocked call — policy forbids destructive ops       |
| `send_email`   | `approval_required`| Call held for human sign-off before proceeding      |

## Prerequisites

Choose one language:

- **Python** — Python 3.9+ (no additional packages required)
- **Node.js** — Node.js 18+ (no additional packages required)

No API keys or external services needed. Both examples run fully offline using a
built-in mock runtime.

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

See [`expected-output.txt`](expected-output.txt) for the reference output from
the Python example. The Node.js output is structurally identical.

## Inspecting the trace

Each audit record printed to stdout contains:

| Field       | Description                                                   |
|-------------|---------------------------------------------------------------|
| `event_id`  | Unique identifier for the audit event                        |
| `timestamp` | ISO 8601 UTC timestamp                                       |
| `agent_id`  | Which agent made the call                                    |
| `tool`      | Which tool was requested                                     |
| `decision`  | `allow`, `deny`, or `approval_required`                      |
| `reason`    | Human-readable policy decision reason                        |
| `inputs`    | Tool call arguments (what the agent passed)                  |
| `outputs`   | Tool result — empty when the call was denied or held         |

In production, Agent Assembly streams these records to:

- The CLI: `aasm audit events --agent <id>`
- The dashboard: **Audit** tab under your agent
- Your SIEM or logging pipeline via the webhook export configured in **Settings → Audit**

## Troubleshooting

**Nothing prints?**  
Ensure you run the script from inside the `python/` or `node/` subdirectory.

**`ModuleNotFoundError` (Python) or `Cannot find module` (Node.js)?**  
This example has no third-party dependencies. Verify your runtime version meets
the prerequisite above.

**Timestamps vary between runs?**  
That is expected — timestamps reflect actual wall-clock time. The
`expected-output.txt` uses placeholder values for the variable fields.

## Notes on production usage

- In production the `AssemblyClient` class is provided by the SDK:
  `agent_assembly` (Python) or `@agent-assembly/sdk` (Node.js).
- The runtime connects to the Agent Assembly gateway to fetch live policies and
  stream audit events over gRPC.
- Audit event retention, export format, and SIEM integration are configured in
  the dashboard under **Settings → Audit**.
- The `.env.example` in each language subdirectory documents the environment
  variables needed to connect to a live gateway.
