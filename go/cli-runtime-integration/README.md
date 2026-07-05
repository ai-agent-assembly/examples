# cli-runtime-integration

Go example showing how to integrate the `aasm` CLI runtime sidecar into a Go agent workflow.

## What this example demonstrates

- Using `assembly.InitAssembly` to auto-start the `aasm` sidecar process
- Handling `assembly.ErrBinaryNotFound` gracefully when `aasm` is not installed
- Falling back to offline mock governance when the sidecar is unavailable
- Using `scripts/run-with-aasm.sh` to orchestrate sidecar startup before running the example
- The relationship between the `aasm` binary, the SDK, and the governance layer

## Prerequisites

| Requirement | Version |
|---|---|
| Go | >= 1.26 |
| Agent Assembly Go SDK | v0.0.1-rc.3 |
| `aasm` binary | Optional — example runs in fallback mode without it |

### Install `aasm` (optional)

```bash
# Homebrew
brew install ai-agent-assembly/tap/aasm

# curl installer (checksum-verified against SHA256SUMS)
curl -fsSL https://agent-assembly.com/install.sh | sh

# go install
go install github.com/ai-agent-assembly/agent-assembly/cmd/aasm@latest
```

If `aasm` is not installed, the example detects `ErrBinaryNotFound` and continues
with an offline mock governance client.

## Setup

```bash
git clone https://github.com/ai-agent-assembly/agent-assembly-examples.git
cd agent-assembly-examples/go/cli-runtime-integration
go mod download
```

## Run

### Without `aasm` (fallback mode — always works)

```bash
go run .
```

### With `aasm` (full sidecar mode)

```bash
bash scripts/run-with-aasm.sh
```

## Expected output (fallback mode — no `aasm` binary)

```text
[runtime] probing for aasm sidecar...
[runtime] aasm binary not found — continuing in offline fallback mode
[runtime] install aasm: brew install ai-agent-assembly/tap/aasm
[runtime] using offline mock governance client
[assembly] governance: ALLOWED  tool=echo input="Hello from the CLI runtime!"
[assembly] tool result: Hello from the CLI runtime!
```

## Expected output (with `aasm` installed)

```text
[runtime] probing for aasm sidecar...
[runtime] sidecar ready at 127.0.0.1:7878
[runtime] sidecar is running — governance calls will reach 127.0.0.1:7878
[runtime] using offline mock client for this example (swap for real transport in production)
[assembly] governance: ALLOWED  tool=echo input="Hello from the CLI runtime!"
[assembly] tool result: Hello from the CLI runtime!
```

## Test

```bash
go test ./...
```

Tests run entirely offline. They verify the `ErrBinaryNotFound` fallback path
without needing `aasm` installed.

## How it works

1. `main.go` calls `assembly.InitAssembly("")` — this probes `127.0.0.1:7878` and,
   if the sidecar is not already running, finds and spawns the `aasm` binary.
2. If `assembly.ErrBinaryNotFound` is returned, the example logs the install hint
   and falls back to the offline mock governance client.
3. If the sidecar is reachable, `buildGovernanceClient` logs the sidecar address and returns
   the offline mock client. Swap this for a real transport-backed `GovernanceClient` in production.
4. A governed `echoTool` call is made through `assembly.WrapTools`.
5. `scripts/run-with-aasm.sh` handles sidecar startup orchestration for CI environments.

## CLI/runtime dependency

This example depends on the `aasm` binary at runtime for the full sidecar path.
The binary is **not bundled** with the Go SDK — it must be installed separately.

If `aasm` is unavailable, `assembly.InitAssembly` returns `assembly.ErrBinaryNotFound`
with a copy-pasteable install command. The example treats this as a non-fatal condition
and continues with the mock client.

## Troubleshooting

| Problem | Fix |
|---|---|
| `aasm binary not found` | Install via Homebrew or `curl` — see the install section above. |
| `sidecar failed to start` | Check `.aasm-runtime.log` in the working directory. |
| `init requires running sidecar` | The sidecar may not have started in time. Re-run or increase the wait in `run-with-aasm.sh`. |
| Port 7878 in use | Another `aasm` instance is already running. The example will connect to it. |

## Go SDK docs

- [`assembly.InitAssembly`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#InitAssembly)
- [`assembly.ErrBinaryNotFound`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#ErrBinaryNotFound)
- [`assembly.Init`](https://pkg.go.dev/github.com/ai-agent-assembly/go-sdk/assembly#Init)

## Back to Go examples

[← Go Examples](../README.md)
