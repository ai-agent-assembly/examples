# Agent Assembly Concepts

This document explains the core concepts behind Agent Assembly so you can understand what each example in this repository is demonstrating.

## The problem Agent Assembly solves

AI agents make autonomous tool calls — web searches, database queries, code execution, API calls to external services. Without a governance layer, those calls happen unchecked: no policy enforcement, no audit trail, no ability to pause and ask a human before a sensitive action is taken.

Agent Assembly intercepts those tool calls before they execute. It can allow, block, or redirect them according to configurable policy rules, log every call to an audit trail, and raise human-in-the-loop approval gates for high-risk actions.

## The three interception layers

Agent Assembly is designed to be deployed incrementally. Each layer adds coverage independently.

### 1. SDK layer (in-process)

The language SDKs — `agent-assembly` for Python, `@agent-assembly/sdk` for Node.js, and `github.com/ai-agent-assembly/go-sdk` for Go — wrap your agent's tool-calling code directly. The SDK calls into a thin Rust shim that:

- Emits a governance event to the gateway before the tool executes.
- Applies an allow/deny decision returned by the gateway.
- Records the outcome in the audit log.

This is the **fastest** interception path. Requires SDK adoption by the agent application.

### 2. Sidecar proxy (`aa-proxy`)

A MitM HTTPS proxy that intercepts outbound TLS connections from the agent process. Works without modifying application code: configure the agent's HTTP client to use the proxy, and the proxy enforces network-egress policy on every outbound request.

Useful when you cannot modify application code or want a second layer of defense.

### 3. eBPF probes (`aa-ebpf`)

Kernel-level hooks attached to SSL library uprobes and process exec/file syscalls. Catches what the SDK or proxy layers miss, including bypass attempts. Linux-only; requires elevated privileges.

## The gateway

The `aa-gateway` service is the central brain. It:

- Holds the **agent registry** — which agents are known, their identity, their allowed capabilities.
- Evaluates the **policy engine** — a rule set defining which tool calls are allowed, which are blocked, and which require approval.
- Tracks **per-team budgets** — call count, token spend, cost ceilings.
- Exposes a **gRPC interface** for SDKs and a **REST/OpenAPI interface** for the dashboard and external tooling.

## Key concepts

### Policy enforcement

A policy rule matches a tool call by agent identity, tool name, argument patterns, or context metadata. Matched calls are either allowed, blocked with a reason, or routed to an approval gate.

### Approval gates

When a tool call matches an approval-required rule, the gateway pauses execution and raises a notification. A human operator (or an automated approver) responds with allow or deny. The agent resumes or fails accordingly.

### Audit and trace

Each tool call that passes through Agent Assembly generates an audit event: agent identity, tool name, arguments (optionally redacted), timestamp, policy decision, and outcome. Events are written to the audit log and can be forwarded to external observability systems.

### Budget controls

The gateway tracks cumulative resource usage per team or per agent: API call counts, LLM token spend, estimated cost. Calls that would exceed a configured ceiling are automatically blocked.

## Further reading

- [Choosing an example](./choosing-an-example.md) — find the right sub-project for your use case.
- [Root README](../README.md) — navigation table and contribution guide.
- [Agent Assembly source repository](https://github.com/ai-agent-assembly/agent-assembly) — the monorepo with the full implementation.
