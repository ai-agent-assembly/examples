# Go Examples

Runnable Go examples showing how to integrate Agent Assembly with Go-based AI agent applications.

## What lives here

| Sub-project | What it demonstrates |
|---|---|
| [`basic-agent/`](./basic-agent/README.md) | Minimal Go SDK initialization and a governed tool call |
| [`tool-policy/`](./tool-policy/README.md) | Explicit allow/deny policy behavior around Go tool execution |
| [`cli-runtime-integration/`](./cli-runtime-integration/README.md) | Integrating the `aasm` CLI runtime sidecar with a Go agent |

All examples use the [`github.com/AI-agent-assembly/go-sdk`](https://pkg.go.dev/github.com/AI-agent-assembly/go-sdk) Go module.

## Prerequisites

- Go >= 1.26
- Agent Assembly Go SDK v0.0.1-alpha.2

A live gateway is **not required** to run any of these examples — each uses an
offline mock `GovernanceClient` by default so you can explore governance behavior
locally without infrastructure.

## Quick start

```bash
# Pick an example
cd go/basic-agent
go mod download
go run .
```

## Sub-project structure

Each sub-project is a standalone Go module:

```text
go/<example-name>/
  README.md                 ← prerequisites, setup, run, expected output, troubleshooting
  go.mod                    ← standalone module declaration
  go.sum                    ← pinned dependency checksums
  main.go                   ← entry point
  policy.go                 ← GovernanceClient implementation (mock or rule-based)
  *_test.go                 ← smoke tests (deterministic, no external calls)
```

## CI

Go examples are verified by `.github/workflows/verify-go.yml` on every push and
pull request that touches the `go/` directory.

## Back to root

[← Agent Assembly Examples](../README.md)
