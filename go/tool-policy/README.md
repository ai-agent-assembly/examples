# tool-policy

Go example showing explicit allow and deny behavior using Agent Assembly policy governance.

## What this example demonstrates

- Defining multiple tools with different risk profiles
- Configuring a `GovernanceClient` with per-tool allow/deny rules
- Observing an **allowed** tool call complete normally
- Observing a **denied** tool call return `assembly.PolicyViolationError`
- How policy decisions are communicated through the SDK layer

## Prerequisites

| Requirement | Version |
|---|---|
| Go | >= 1.26 |
| Agent Assembly Go SDK | v0.0.1-rc.3 |

No live gateway is required. Policy rules are applied by an in-process mock client.

## Setup

```bash
git clone https://github.com/ai-agent-assembly/examples.git
cd examples/go/tool-policy
go mod download
```

## Run

```bash
go run .
```

## Expected output

```text
[policy] client loaded: read-file=ALLOW, delete-file=DENY

[tool] calling: read-file  input="config.yaml"
[policy] ALLOWED  tool=read-file
[tool] result: (contents of config.yaml)

[tool] calling: delete-file  input="config.yaml"
[policy] DENIED   tool=delete-file  reason="delete operations are blocked by policy"
[tool] error: assembly: policy violation: tool=delete-file reason=delete operations are blocked by policy
```

## Test

```bash
go test ./...
```

All tests run offline — no gateway required.

## How it works

1. `tools.go` defines `readFileTool` (safe) and `deleteFileTool` (destructive).
2. `policy.go` defines `policyClient` — a `GovernanceClient` that checks the tool name and returns `Denied: true` for the blocked tool.
3. `main.go` wraps both tools with `assembly.WrapTools` using `policyClient`.
4. It then calls each tool and shows the outcome.

This pattern maps directly to production behavior: swap `policyClient` for a real gateway client and the same SDK wrapping logic controls your AI agent's tool access.

## Troubleshooting

| Problem | Fix |
|---|---|
| `go: module not found` | Run `go mod download` — requires internet access on first run. |
| Both tools allowed | Verify you are running `go run .` inside `go/tool-policy/`, not the repo root. |

## Go SDK docs

- [`assembly.WrapTools`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#WrapTools)
- [`assembly.PolicyViolationError`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#PolicyViolationError)
- [`assembly.GovernanceClient`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#GovernanceClient)

## Back to Go examples

[← Go Examples](../README.md)
