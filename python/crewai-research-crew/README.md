# crewai-research-crew

Demonstrates how [Agent Assembly](https://github.com/ai-agent-assembly/examples)
governs a **multi-agent** [CrewAI](https://docs.crewai.com/)-style research crew.
Three agents collaborate, delegate to one another, and every governed tool call
is attributed to the acting agent with the full delegation chain captured on the
audit event.

## What this example demonstrates

- A three-agent crew: **researcher → writer → critic**, each with a distinct role.
- **Agent-delegation tracking** — every governed call records an `AuditEvent`
  whose `call_stack` is the delegation chain (`parent → agent → tool`), using the
  SDK's real `agent_assembly.types.AuditEvent` and `CallStackNode`.
- **Multi-agent governance** under one policy:
  - **File-write approval** — any agent that attempts `write_file` is gated; the
    decision is `pending` until an approver signs off (rejected in this demo).
  - **Shared daily budget** — tool calls across all three agents are metered
    against a single `$2.00 / day` cap.
- `--mock` mode: the whole crew runs offline with **no `crewai` install and no
  API keys**, so CI can run it.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | >= 3.12 |
| [uv](https://github.com/astral-sh/uv) | latest |
| Agent Assembly Python SDK | >= 0.0.1rc3 |

The mock demo needs no gateway, no `crewai`, and no API keys. The optional
`live` extra (`crewai`) is only required for the real-crew integration.

## Setup

```bash
cd python/crewai-research-crew
uv sync --extra dev
```

## Run

```bash
uv run python src/main.py --mock
```

`--mock` replays a scripted crew delegation trajectory offline. The example also
auto-falls back to mock mode whenever `OPENAI_API_KEY` is unset.

### Expected governance output

```
================================================================
  Agent Assembly — CrewAI Multi-Agent Research Crew
================================================================

Initializing Agent Assembly (gateway: http://localhost:8080, sdk-only mode)...
  Agent:    crewai-research-crew
  Gateway:  http://localhost:8080
  Mode:     sdk-only (mock (offline))

Crew members:
  • researcher  — Senior Research Analyst
  • writer      — Technical Writer
  • critic      — Editorial Critic

Crew policy (local simulation of gateway policy):
  APPROVAL — any agent attempting a file write must be approved
  BUDGET   — $2.00 / day, shared across all agents
  TRACK    — every call recorded with its delegation call stack

Running crew delegation trajectory:
----------------------------------------------
  [researcher]  (crew entry agent)
    → web_search({"query": "agent governance"})
       ✅ ALLOWED

  [researcher]  (crew entry agent)
    → web_search({"query": "interception layers"})
       ✅ ALLOWED

  [writer]  (delegated by researcher)
    → compose_report({"section": "summary"})
       ✅ ALLOWED

  [critic]  (delegated by writer)
    → review_text({"target": "summary"})
       ✅ ALLOWED

  [critic]  (delegated by writer)
    → write_file({"path": "report.md"})
       ❌ BLOCKED  — Approval for 'write_file' by 'critic' was rejected — the crew may not persist files without sign-off.

Delegation-aware audit events recorded this run:
----------------------------------------------
  ✅ allow web_search      chain: researcher → web_search
  ✅ allow web_search      chain: researcher → web_search
  ✅ allow compose_report  chain: researcher → writer → compose_report
  ✅ allow review_text     chain: writer → critic → review_text
  ❌ deny  write_file      chain: writer → critic → write_file

Final crew budget: spent=$0.25 / limit=$2.00 (12%)

Assembly context shut down.
```

### Governance-output walkthrough

| Step | Acting agent | Delegated by | Governance control | Outcome |
|---|---|---|---|---|
| `web_search` | researcher | — (entry) | shared budget | **ALLOWED**, `$0.05` |
| `web_search` | researcher | — (entry) | shared budget | **ALLOWED**, `$0.05` |
| `compose_report` | writer | researcher | shared budget | **ALLOWED**, `$0.10` |
| `review_text` | critic | writer | shared budget | **ALLOWED**, `$0.05` |
| `write_file` | critic | writer | file-write approval | **BLOCKED** — approval rejected |

The `chain:` column in the audit replay is the delegation call stack each
`AuditEvent` carries: it shows which agent delegated to which, down to the tool.
This is the agent-delegation tracking that distinguishes multi-agent governance
from single-agent governance — a real gateway persists the same call stack so an
operator can see exactly who delegated a blocked action.

To see the approval path succeed instead, construct the policy with an
auto-approving approver (`MockApprover(auto_approve=True)`) — the `write_file`
event then records an `allow` decision.

## Run tests

```bash
uv run pytest tests/ -v
```

## Switching to the live CrewAI integration

1. Install the live extra: `pip install -e '.[live]'` (pulls in `crewai`).
2. Start an Agent Assembly gateway (or use your SaaS workspace URL).
3. Copy `.env.example` to `.env` and fill in your credentials.
4. Configure the approval gate and shared budget in the gateway.
5. Run without `--mock` and with a real LLM provider key:

```bash
AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \
AGENT_ASSEMBLY_API_KEY=your-key \
OPENAI_API_KEY=sk-your-real-key \
uv run python src/main.py
```

In production, map each `CrewMember` onto a `crewai.Agent` and replace
`CrewPolicyEngine` with the gateway-backed interceptor; the SDK enforces the
gateway's policy and emits delegation-aware audit events automatically.

## Links

- [Agent Assembly Python SDK](https://github.com/ai-agent-assembly/python-sdk)
- [Python Examples](../README.md)
