# Live-Core Enforcement Scenario

A **genuine end-to-end** governance example: the *real* Agent Assembly SDK
registers with, and is governed by, a *real* `aa-runtime` + `aa-gateway`. A
policy `deny` actually blocks a tool call before it runs.

This is the opposite of the offline scenarios in this repo. `sidecar-runtime`
(and the others) ship a small SDK-shaped stand-in so they run with bare
runtimes and no gateway — that is what keeps CI green offline. **This scenario
does not stand anything in.** It imports `agent_assembly` for real and talks to
a real core over gRPC/UDS, exactly as a production integration does.

> **Heads-up — gateway image not published yet.** This scenario needs a real
> `aa-gateway` (the runtime alone cannot make the per-tool allow/deny decision).
> The gateway is **not** bundled in the `aa-runtime` image, and
> `ghcr.io/ai-agent-assembly/aa-gateway` is **not published yet**. Until it is,
> `bash scripts/start.sh` cannot pull the gateway image and the stack will not
> run out of the box. See [Gateway image dependency](#gateway-image-dependency).

## The real flow (ADR 0004)

```
  your agent
      │  init_assembly(...)            ← registers the agent DIRECTLY with the gateway (gRPC)
      │  client.check_tool_start(...)  ← pre-execution policy check
      ▼
  Agent Assembly SDK (agent_assembly)
      │  native _core / aa-sdk-client
      │    • register  ──gRPC──────────────────────────►  aa-gateway  :50051
      │    • check     ──UDS──►  aa-runtime  ──gRPC──►     aa-gateway  :50051
      ▼                          (forwards CheckAction)    (policy authority,
                                                            loads policy.yaml)
```

Two distinct transports matter here:

- **Registration** is a *direct* SDK → gateway gRPC call (`AgentLifecycleService.
  Register`). The native client picks the endpoint from `AA_GATEWAY_ENDPOINT`
  (it defaults to `127.0.0.1:50051`).
- **The governed check** (`check_tool_start` → `query_policy`) goes over the
  runtime UDS at `/tmp/aa-runtime-<agent_id>.sock`; the runtime then forwards the
  `CheckAction` to the gateway (its own `AA_GATEWAY_ENDPOINT`). Under
  `enforcement_mode="enforce"`, a gateway `deny` blocks the tool.

The gateway is the **policy authority**: it loads the section-based `policy.yaml`
and decides per tool. The `aa-runtime`'s own (optional) local policy is a coarse
action-type denylist and cannot express per-tool `read_file` vs `delete_file`
rules — which is exactly why a real gateway is required for this scenario.

## What you need

- **Docker** 24+ with Compose v2 (`docker compose`) — brings up the real stack.
- The **native** Agent Assembly Python SDK. The pure-Python wheel alone has no
  `RuntimeClient`; the native extension (built with `maturin`) is required for
  the genuine gRPC/UDS path. The bundled agent `Dockerfile` builds it for you.
- The published runtime image `ghcr.io/ai-agent-assembly/aa-runtime:latest`.
- The published gateway image `ghcr.io/ai-agent-assembly/aa-gateway:latest`
  — **not available yet**, see [Gateway image dependency](#gateway-image-dependency).

## Run it

```bash
cd scenarios/live-core-enforcement
bash scripts/start.sh      # starts aa-gateway + aa-runtime, then runs the agent
```

`start.sh` brings up the gateway (loading `policy.yaml`) and the runtime, gates
their readiness **from the host** (see below), then runs the agent and streams
the allow/deny output. Tear down:

```bash
bash scripts/stop.sh
```

> **Why readiness is checked from the host:** the `aa-runtime` image is
> distroless — it has no `/bin/sh` and no `wget`, so a Compose
> `healthcheck: ["CMD-SHELL", ...]` can never execute inside it (it fails with
> `exec: "/bin/sh": no such file or directory`, which used to leave the agent
> stuck on `depends_on: condition: service_healthy`). Instead `start.sh` polls
> the runtime's published `:8080/ready` endpoint and the gateway's `:50051` gRPC
> port from the host, where `curl` and a TCP probe are available.

### Running the agent outside Docker

If you already have a runtime + gateway running locally and a native SDK build:

```bash
pip install "agent-assembly==0.0.1rc6"   # plus the native extension (maturin)
cp python-agent/.env.example .env       # then export the vars (incl. AA_GATEWAY_ENDPOINT)
python python-agent/agent.py
```

## The policy

`policy.yaml` is a **real** section-based Agent Assembly policy (same schema as
`agent-assembly/schemas/examples/balanced.yaml`). The **gateway** loads it and
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

## Gateway image dependency

This scenario's per-tool allow/deny **requires a real `aa-gateway`**, for two
independent reasons:

1. **Registration** (`init_assembly`) is a direct SDK → gateway gRPC call. With
   no gateway it fails with
   `RuntimeError: gateway gRPC endpoint is unreachable for registration`.
2. **The per-tool decision** can only be made by the gateway's section-based
   policy engine. The `aa-runtime`'s local policy is an action-*type* denylist
   and cannot distinguish `read_file` from `delete_file`.

The gateway is **not** bundled in the `aa-runtime` image, and as of this writing
`ghcr.io/ai-agent-assembly/aa-gateway` is **not published** (the org publishes
`aa-runtime` and the SDK base images only). Until a version-matched gateway
image is published, `docker compose pull`/`up` cannot fetch the gateway and the
stack cannot complete end-to-end. The compose file and scripts here are wired
for the correct topology so the scenario works the moment that image lands.

If you have a local checkout of the `agent-assembly` monorepo you can build and
run the gateway yourself for a manual end-to-end run:

```bash
# in the agent-assembly monorepo
cargo build -p aa-gateway --release
./target/release/aa-gateway --policy /path/to/policy.yaml --listen 0.0.0.0:50051
```

…then point the runtime and agent `AA_GATEWAY_ENDPOINT` at it.

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
  `bash scripts/start.sh` with Docker and access to **both** the runtime and the
  gateway images (see [Gateway image dependency](#gateway-image-dependency)), or
  in a dedicated opt-in CI job that publishes/builds a real gateway. Bringing up
  the real Rust stack is too heavy for the default offline smoke matrix.

This keeps CI truthful: it proves the example is correct code against the real
SDK surface, without pretending to have run a gateway it cannot start.

## Troubleshooting

**`init_assembly` fails with `gateway gRPC endpoint is unreachable for registration`?**
The agent could not reach the gateway for registration. Confirm the `aa-gateway`
service is up and serving `:50051`, and that **`AA_GATEWAY_ENDPOINT`** is set on
the agent (the native client reads that, not `AA_GATEWAY_URL`; it defaults to
`127.0.0.1:50051`, which is wrong inside a container). See also
[Gateway image dependency](#gateway-image-dependency).

**`init_assembly` fails / agent registers but every call is allowed?**
Either the native extension is not loaded (no runtime fast path to query) or the
runtime is not forwarding to the gateway. Confirm
`python -c "import agent_assembly._core"` succeeds (build it with
`maturin develop` against a source checkout), that `AA_RUNTIME_SOCKET` points at
the socket the runtime created, and that the runtime's `AA_GATEWAY_ENDPOINT`
points at the gateway so it forwards `CheckAction` there.

**Gateway / runtime not coming up?**
`docker compose logs aa-gateway aa-runtime`. Ensure both images are pullable and
`policy.yaml` is mounted into the gateway at `/etc/aa/policy.yaml`. The runtime
image is distroless, so it has no in-container healthcheck — readiness is gated
from the host (see [Run it](#run-it)).

**`AA_AGENT_ID` mismatch?**
The socket name embeds the agent id. The `aa-runtime` and `live-agent` services
must use the **same** `AA_AGENT_ID`.
