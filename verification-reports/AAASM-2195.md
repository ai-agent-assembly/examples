# Verification Report — AAASM-2195

**Story:** Add Go SDK and CLI runtime examples to agent-assembly-examples  
**Verified by:** AAASM-2277  
**Date:** 2026-05-30  
**SDK version:** github.com/AI-agent-assembly/go-sdk v0.0.1-alpha.2

---

## Acceptance Criteria

### ✅ `go/README.md` routes Go developers to each example

`go/README.md` (AAASM-2276 / PR #16) contains a routing table with hyperlinks to all
three sub-project READMEs:

| Link | Target |
|---|---|
| `basic-agent/` | `go/basic-agent/README.md` |
| `tool-policy/` | `go/tool-policy/README.md` |
| `cli-runtime-integration/` | `go/cli-runtime-integration/README.md` |

---

### ✅ At least three Go sub-projects exist

| Sub-project | PR | Status |
|---|---|---|
| `go/basic-agent/` | #8 (AAASM-2273) | Open |
| `go/tool-policy/` | #10 (AAASM-2274) | Open |
| `go/cli-runtime-integration/` | #14 (AAASM-2275) | Open |

---

### ✅ Each example has a README, run command, and expected output

| Sub-project | README | Run command | Expected output |
|---|---|---|---|
| `basic-agent` | `go/basic-agent/README.md` | `go run .` | Offline mock allow message + tool result |
| `tool-policy` | `go/tool-policy/README.md` | `go run .` | ALLOWED + DENIED output for two tools |
| `cli-runtime-integration` | `go/cli-runtime-integration/README.md` | `go run .` | Fallback mode + tool result |

---

### ✅ Each example has a smoke test runnable in CI (`go test ./...` passes)

Tests run locally (2026-05-30) with `go test ./... -v`:

**basic-agent** — `ok example.com/basic-agent`
- `TestEchoToolReturnsInput` PASS
- `TestEchoToolName` PASS
- `TestWrappedToolAllowedByMock` PASS
- `TestWrappedToolDeniedByClient` PASS

**tool-policy** — `ok example.com/tool-policy`
- `TestReadFileToolReturnsContents` PASS
- `TestDeleteFileToolReturnsDeleted` PASS
- `TestPolicyClientAllowsReadFile` PASS
- `TestPolicyClientDeniesDeleteFile` PASS
- `TestAllBlockedToolsAreDenied` PASS

**cli-runtime-integration** — `ok example.com/cli-runtime-integration`
- `TestEchoToolReturnsInput` PASS
- `TestStartSidecarReturnsFalseWhenBinaryAbsent` PASS
- `TestMockClientAllowsToolCall` PASS
- `TestBuildGovernanceClientReturnsMock` PASS
- `TestInitAssemblyReturnsBinaryNotFoundInEmptyPath` PASS

All 14 tests pass. No network access required.

---

### ✅ CLI/runtime example documents `aasm` prerequisite and fallback behavior

`go/cli-runtime-integration/README.md` includes:
- Install instructions (Homebrew, curl, go install)
- What happens when `aasm` is absent (fallback to offline mock)
- Expected output for both paths (with and without sidecar)
- How `assembly.InitAssembly` and `assembly.ErrBinaryNotFound` interact
- `scripts/run-with-aasm.sh` for full sidecar orchestration

---

### ✅ No secrets committed

Verified: no `.env` files, API keys, private tokens, or secret values exist in any
of the four PRs (#8, #10, #14, #16). Each example uses only environment variable
documentation via README comments. No `.env.example` was needed since examples use
the offline mock by default.

---

### ✅ Root README links to the Go examples section

`README.md` routing table (pre-existing from AAASM-2192):

```markdown
| Use Go | [`go/`](./go/README.md) |
```

This entry routes to `go/README.md`, which now routes to each sub-project.

---

### ✅ CI `verify-go.yml` added

`.github/workflows/verify-go.yml` (AAASM-2276 / PR #16):
- Triggers on `push` and `pull_request` to `main` when `go/**` or the workflow itself changes
- Matrix strategy: `basic-agent`, `tool-policy`, `cli-runtime-integration`
- Uses `actions/setup-go@v5` with Go 1.26 and go.sum caching per sub-project
- Handles sub-projects not yet present (directory existence check before running tests)

---

## Summary

All 7 acceptance criteria for AAASM-2195 are satisfied. Four PRs are pending merge:

| PR | Ticket | Scope |
|---|---|---|
| #8 | AAASM-2273 | `go/basic-agent/` |
| #10 | AAASM-2274 | `go/tool-policy/` |
| #14 | AAASM-2275 | `go/cli-runtime-integration/` |
| #16 | AAASM-2276 | `verify-go.yml` CI + `go/README.md` |
