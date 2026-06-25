# Live-Core Enforcement Scenario

A **genuine end-to-end** governance example: the *real* Agent Assembly SDK
registers with, and is governed by, a *real* `aa-runtime` + `aa-gateway`. A
policy `deny` actually blocks a tool call before it runs.

This is the opposite of the offline scenarios in this repo. `sidecar-runtime`
(and the others) ship a small SDK-shaped stand-in so they run with bare
runtimes and no gateway — that is what keeps CI green offline. **This scenario
does not stand anything in.** It imports `agent_assembly` for real and talks to
a real core over gRPC/UDS, exactly as a production integration does.

## The real flow (ADR 0004)

```
  your agent
      │  init_assembly(...)            ← registers the agent with the gateway
      │  client.check_tool_start(...)  ← pre-execution policy check
      ▼
  Agent Assembly SDK (agent_assembly)
      │  native _core / aa-sdk-client (gRPC over a Unix domain socket)
      ▼
  aa-runtime sidecar  ──gRPC──►  aa-gateway   (the policy authority)
                                   loads policy.yaml
```

The SDK's native `RuntimeClient` connects to the runtime at
`/tmp/aa-runtime-<agent_id>.sock` (override with `AA_RUNTIME_SOCKET`),
`init_assembly` registers the agent on startup, and each `check_tool_start`
forwards to the runtime's `query_policy` → the gateway. Under
`enforcement_mode="enforce"`, a gateway `deny` blocks the tool.

## What you need

- **Docker** 24+ with Compose v2 (`docker compose`) — brings up the real stack.
- The **native** Agent Assembly Python SDK. The pure-Python wheel alone has no
  `RuntimeClient`; the native extension (built with `maturin`) is required for
  the genuine gRPC/UDS path. The bundled agent `Dockerfile` builds it for you.
- Access to the published runtime image
  `ghcr.io/ai-agent-assembly/aa-runtime:latest` (or a local build of it).

## Run it

```bash
cd scenarios/live-core-enforcement
bash scripts/start.sh      # builds + starts aa-runtime, then runs the agent
```

`start.sh` brings up the real runtime/gateway with `policy.yaml`, waits for its
health check, then runs the agent and streams the allow/deny output. Tear down:

```bash
bash scripts/stop.sh
```

### Running the agent outside Docker

If you already have a runtime + gateway running locally and a native SDK build:

```bash
pip install "agent-assembly>=0.0.1b5"   # plus the native extension (maturin)
cp python-agent/.env.example .env       # then export the vars
python python-agent/agent.py
```

## The policy

`policy.yaml` is a **real** section-based Agent Assembly policy (same schema as
`agent-assembly/schemas/examples/balanced.yaml`). The gateway loads it and
evaluates it on every check. The relevant section:

```yaml
tools:
  read_file:    { allow: true,  limit_per_hour: 50 }   # permitted
  delete_file:  { allow: false }                       # blocked
```

## Expected output

```
=== Agent Assembly — Live-Core Enforcement Example ===
...
  → read_file(path='/data/report.csv')
  [GATEWAY] decision=allow
    ✓ allowed — tool would execute

  → delete_file(path='/data/important.csv')
  [GATEWAY] decision=deny    reason=tool 'delete_file' is denied by policy
    ✗ blocked — tool did NOT execute

Total tool calls: 2  |  blocked by policy: 1
```

(The exact `reason` and `audit_id` strings come from the gateway and may differ
by version; `expected-output.txt` shows the shape.)

## CI and what is verified

The examples repo's CI runs **offline with bare runtimes** — it cannot build and
run a real Rust gateway inline, and faking the SDK would defeat the purpose of
this scenario. So CI honestly splits the two concerns:

- **Offline-safe smoke (runs in CI):** `scripts/check-offline.py` asserts the
  example *code* is valid and faithful — `agent.py` parses and imports the
  **real** `agent_assembly` SDK (no shim), and `policy.yaml` is a valid
  section-based policy that allows `read_file` and denies `delete_file`. It does
  **not** call `init_assembly` (that would require a gateway).
- **Live end-to-end (manual / opt-in):** the real allow/deny flow runs only via
  `bash scripts/start.sh` with Docker and access to the runtime image, or in a
  dedicated opt-in CI job that pulls/builds a real gateway. Bringing up the real
  Rust stack is too heavy for the default offline smoke matrix.

This keeps CI truthful: it proves the example is correct code against the real
SDK surface, without pretending to have run a gateway it cannot start.

## Troubleshooting

**`init_assembly` fails / agent registers but every call is allowed?**
The native extension is probably not loaded, so there is no runtime fast path to
register against or query. Confirm `python -c "import agent_assembly._core"`
succeeds (build it with `maturin develop` against a source checkout), and that
`AA_RUNTIME_SOCKET` points at the socket the runtime created.

**Runtime container not healthy?**
`docker compose logs aa-runtime`. Ensure the image is pullable and `policy.yaml`
mounted at `/etc/aa/policy.yaml`.

**`AA_AGENT_ID` mismatch?**
The socket name embeds the agent id. The `aa-runtime` and `live-agent` services
must use the **same** `AA_AGENT_ID`.
