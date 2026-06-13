# Agent Assembly Examples

Runnable examples showing how to integrate [Agent Assembly](https://github.com/ai-agent-assembly/agent-assembly) with real AI agent frameworks, enforce policies, gate approvals, capture audit traces, and control runtime budgets.

## What is Agent Assembly?

Agent Assembly is a multi-layer AI agent governance platform that intercepts, inspects, and enforces policies on tool calls made by AI agents — without requiring you to rewrite your agent code. It works via three independently deployable layers: SDK wrappers (Python, Node.js, Go), a sidecar MitM proxy, and kernel-level eBPF probes. A central gateway holds the agent registry, evaluates policies, tracks budgets, and exposes gRPC and HTTP APIs for observability and control.

## Official docs & SDKs

These examples are the runnable companion to the official documentation and the
language SDKs. Learn by running small, framework-specific examples for Python,
Node.js/TypeScript, Go, policy enforcement, approvals, audit, trace, and runtime
workflows — then go deeper in the docs.

| Resource | Link |
|---|---|
| Documentation hub | <https://ai-agent-assembly.github.io/agent-assembly-docs/> |
| Core runtime & CLI | [agent-assembly](https://github.com/ai-agent-assembly/agent-assembly) |
| Python SDK | [python-sdk](https://github.com/ai-agent-assembly/python-sdk) |
| Node.js / TypeScript SDK | [node-sdk](https://github.com/ai-agent-assembly/node-sdk) |
| Go SDK | [go-sdk](https://github.com/ai-agent-assembly/go-sdk) |

## Who is this repo for?

- **Application developers** who are adding Agent Assembly to an existing Python, Node.js, or Go agent application.
- **Platform engineers** who are deploying Agent Assembly as a runtime governance layer.
- **Evaluators** who want to understand policy enforcement, approval gates, audit tracing, and budget controls through working code before committing to adoption.

## Quick navigation

| You want to…                        | Start here                                         |
|-------------------------------------|----------------------------------------------------|
| Use Python + LangChain              | [`python/`](./python/README.md)                    |
| Use Node.js / TypeScript + LangChain| [`node/`](./node/README.md)                        |
| Use Go                              | [`go/`](./go/README.md)                            |
| Explore policy enforcement          | [`scenarios/policy-enforcement/`](./scenarios/policy-enforcement/README.md) |
| Understand approval gates           | [`scenarios/approval-gates/`](./scenarios/approval-gates/README.md)         |
| See audit/trace output              | [`scenarios/audit-trace/`](./scenarios/audit-trace/README.md) |
| Enforce budget guardrails           | [`scenarios/budget-limits/`](./scenarios/budget-limits/README.md) |
| Run with a local sidecar runtime    | [`scenarios/sidecar-runtime/`](./scenarios/sidecar-runtime/README.md) |
| Read core concepts first            | [`docs/concepts.md`](./docs/concepts.md)           |
| Choose the right example            | [`docs/choosing-an-example.md`](./docs/choosing-an-example.md) |

## Advanced scenarios: observability and runtime controls

The `scenarios/` directory contains cross-language examples that demonstrate
Agent Assembly's runtime governance features. These are the fastest path to
understanding what Agent Assembly does at the product level — no framework
setup required, no API keys needed.

| Scenario | What it demonstrates | Quick start |
|---|---|---|
| [`audit-trace`](./scenarios/audit-trace/) | Governed tool calls producing `allow`, `deny`, and `approval_required` audit records | `python scenarios/audit-trace/python/agent.py` |
| [`budget-limits`](./scenarios/budget-limits/) | Budget guardrails blocking tool calls when a session cost ceiling is hit | `python scenarios/budget-limits/python/agent.py` |
| [`sidecar-runtime`](./scenarios/sidecar-runtime/) | Running agents against a local Agent Assembly gateway via Docker Compose | `bash scenarios/sidecar-runtime/scripts/start.sh` |

All three scenarios include Python and Node.js examples. They run **offline by
default** — no live gateway needed unless you opt into the Docker Compose path.

## Prerequisites

Install the prerequisites for the ecosystem you want to run.

### Python examples

```bash
python3 --version   # requires Python >= 3.12
pip install uv      # optional but recommended
```

### Node.js / TypeScript examples

```bash
node --version    # requires Node.js >= 20 LTS
pnpm --version    # install via: npm install -g pnpm
```

### Go examples

```bash
go version   # requires Go >= 1.22
```

### Agent Assembly runtime (all examples)

Each example sub-project documents which Agent Assembly component it requires (SDK version, gateway address, sidecar config). See the sub-project `README.md` for the exact setup.

## Security

**No secrets are ever committed to this repository.**

- Configuration files that require API keys or connection strings provide a `.env.example` template only.
- Copy `.env.example` to `.env`, fill in your values, and keep that file local — `.env` is listed in `.gitignore`.
- Never paste real credentials into a file tracked by git.

## Compatibility

Each example sub-project pins or documents the Agent Assembly SDK and gateway version it was written and tested against. Check the sub-project `README.md` for the `requires:` block before running.

## Contributing an example

1. Pick a directory: `python/`, `node/`, `go/`, or `scenarios/`.
2. Create a sub-directory named after the framework or scenario (e.g. `python/langchain-basic-agent/`).
3. Add a `README.md` inside the sub-directory with:
   - **What it demonstrates** (one paragraph)
   - **Prerequisites** (language version, Agent Assembly version, any API keys needed)
   - **Setup** (`git clone`, install deps)
   - **Run** (exact command and expected output)
   - **Troubleshooting** (common errors and fixes)
4. Add a `.env.example` if the example needs any configuration.
5. Open a PR with title `[AAASM-XXXX] <GitEmoji> (<scope>): <summary>`.

See [`docs/concepts.md`](./docs/concepts.md) for background on how Agent Assembly works before building an example.

## Repository layout

```text
agent-assembly-examples/
  README.md                     ← you are here
  LICENSE                       ← Apache-2.0
  .gitignore
  docs/
    concepts.md                 ← Agent Assembly core concepts
    choosing-an-example.md      ← decision guide: which example to run first
  python/
    README.md                   ← Python examples index
  node/
    README.md                   ← Node.js / TypeScript examples index
  go/
    README.md                   ← Go examples index
  scenarios/
    README.md                   ← Cross-language scenario examples index
    policy-enforcement/         ← Allow/deny policy enforcement scenario
    approval-gates/             ← Human-in-the-loop approval gates scenario
    audit-trace/                ← Governed tool calls + audit record inspection
    budget-limits/              ← Budget guardrails and cost ceiling enforcement
    sidecar-runtime/            ← Local Agent Assembly runtime via Docker Compose
  .github/
    workflows/
      README.md                 ← CI workflow documentation
```
