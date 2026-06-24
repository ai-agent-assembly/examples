# basic-agent

Minimal Go example showing how to initialize the Agent Assembly Go SDK and execute a governed tool call.

## What this example demonstrates

- Importing and initializing the Agent Assembly Go SDK
- Defining a tool that satisfies the `assembly.Tool` interface
- Wrapping a tool with `assembly.WrapTools` for governance interception
- Observing the allow decision path through console output
- Using an offline mock `GovernanceClient` for local development and CI

## Prerequisites

| Requirement | Version |
|---|---|
| Go | >= 1.26 |
| Agent Assembly Go SDK | v0.0.1-beta.3 |

A live Agent Assembly gateway is **not required** to run this example. It uses an
offline mock `GovernanceClient` by default. To use a real gateway, replace `mockClient`
in `policy.go` with a transport-backed `GovernanceClient` implementation.

## Setup

```bash
git clone https://github.com/ai-agent-assembly/agent-assembly-examples.git
cd agent-assembly-examples/go/basic-agent
go mod download
```

## Run

```bash
go run .
```

## Expected output

```text
[assembly] using offline mock governance client
[assembly] governance: ALLOWED  tool=echo input="Hello, Agent Assembly!"
[assembly] tool result: Hello, Agent Assembly!
```

## Test

```bash
go test ./...
```

Tests run entirely offline using the mock client — no gateway required.

## How it works

1. An `echoTool` implements `assembly.Tool` (Name, Description, Call).
2. `assembly.WrapTools` wraps the tool with a `GovernanceClient`.
3. Before each `Call`, the wrapper sends a `CheckRequest` to the client.
4. The client returns a `Decision` (allowed or denied).
5. Allowed calls proceed to the inner tool; denied calls return `PolicyViolationError`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `go: module github.com/ai-agent-assembly/go-sdk: not found` | Run `go mod download` or check network access to `proxy.golang.org`. |
| `init requires a running sidecar` | Only occurs when `assembly.Init()` is called with an explicit gateway URL. This example uses the mock client only — `Init()` is never called. |
| Unexpected denial | Verify you are not running a modified `policy.go` that returns `Denied: true`. |

## Go SDK docs

- Module: [`github.com/ai-agent-assembly/go-sdk`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk)
- `assembly.Tool` interface
- `assembly.WrapTools` function
- `assembly.GovernanceClient` interface

## Back to Go examples

[← Go Examples](../README.md)
