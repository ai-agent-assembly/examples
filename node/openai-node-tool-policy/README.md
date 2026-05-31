# openai-node-tool-policy

An OpenAI Node SDK-style agent example showing how to enforce tool policies using the Agent Assembly Node.js SDK.

## What this example demonstrates

- Defining tools in OpenAI function-calling format
- Calling `initAssembly()` to register the agent with the gateway (or offline/noop mode)
- Wrapping tool dispatch with `withAssembly()` for policy enforcement
- One **allowed** tool call (`search_web`) — executes and returns mock results
- One **denied** tool call (`send_email`) — blocked at the policy layer before execution
- Audit events emitted on every tool invocation

## Prerequisites

- Node.js >= 20 LTS
- pnpm (`npm install -g pnpm`)

## Install

```bash
pnpm install
```

## Run

```bash
pnpm start
```

### Expected output

```
=== OpenAI Node SDK-style Agent Assembly Example ===

Available tools: search_web, send_email

Simulating OpenAI tool call: search_web
[POLICY ALLOW] search_web: Search results for "Agent Assembly governance": [mock result 1] [mock result 2]

Simulating OpenAI tool call: send_email (should be denied)
[POLICY DENY] send_email: External communication requires human approval before sending.

Audit events emitted to gateway (or noop in offline mode).
```

## Test

```bash
pnpm test
```

All tests run offline — no gateway or API key required.

## TypeScript type check

```bash
pnpm typecheck
```

## Real-provider mode (optional)

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Set AAASM_GATEWAY_URL and optionally OPENAI_API_KEY
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Cannot find module '@agent-assembly/sdk'` | Run `pnpm install` |
| Gateway connection refused | Remove `AAASM_GATEWAY_URL` from `.env` to use offline mode |
| TypeScript errors | Run `pnpm typecheck` |

## Links

- [Agent Assembly Node.js SDK](https://github.com/AI-agent-assembly/node-sdk)
- [Node.js examples overview](../README.md)
- [Root examples README](../../README.md)
