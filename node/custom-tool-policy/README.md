# custom-tool-policy

A minimal TypeScript example showing how to use Agent Assembly governance directly — no agent framework required.

## What this example demonstrates

- Using `initAssembly()` and `withAssembly()` from `@agent-assembly/sdk` without any external agent framework
- Defining raw TypeScript tool functions and wrapping them for governance
- One **allowed** tool call (`read_file`) — executes and returns mock output
- One **denied** tool call (`write_file`) — blocked at the policy layer
- Audit events emitted to the gateway (or noop in offline mode)

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
=== Custom Tool Policy — Minimal TypeScript Example ===

No agent framework required. Using @agent-assembly/sdk directly.

Calling allowed tool: read_file
[POLICY ALLOW] read_file: Contents of "/data/report.txt": [mock file contents line 1, line 2]

Calling denied tool: write_file
[POLICY DENY] write_file: Write operations to the filesystem require explicit approval.

All tool calls governed by policy. Audit emitted to gateway (or noop).
```

## Test

```bash
pnpm test
```

No gateway or API key required. All tests run offline.

## TypeScript type check

```bash
pnpm typecheck
```

## Note on `.env.example`

This example uses only mock/offline mode. No provider keys or gateway URL are needed. To connect to a real gateway, set `AAASM_GATEWAY_URL` in your environment directly.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Cannot find module '@agent-assembly/sdk'` | Run `pnpm install` |
| TypeScript errors | Run `pnpm typecheck` and check the Node.js version |

## Links

- [Agent Assembly Node.js SDK](https://github.com/AI-agent-assembly/node-sdk)
- [Node.js examples overview](../README.md)
- [Root examples README](../../README.md)
