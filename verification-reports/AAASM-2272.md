# Verification Report — AAASM-2272

**Story**: AAASM-2194 — Add Node.js and TypeScript framework examples to agent-assembly-examples  
**Verified by**: AAASM-2272 (Verify AAASM-2194 Node.js examples acceptance criteria)  
**Date**: 2026-05-30  
**Repo**: https://github.com/AI-agent-assembly/agent-assembly-examples

## Summary

All 8 acceptance criteria: **PASS**

## AC Verification

| # | Acceptance Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `node/README.md` routes Node/TypeScript developers to each example | ✅ PASS | See below |
| 2 | At least three Node/TypeScript sub-projects exist | ✅ PASS | See below |
| 3 | Each example has install/run/test scripts | ✅ PASS | See below |
| 4 | Each example has a deterministic smoke test | ✅ PASS | See below |
| 5 | Examples compile under TypeScript strict mode | ✅ PASS | See below |
| 6 | Mock/offline mode is the default | ✅ PASS | See below |
| 7 | No secrets are committed | ✅ PASS | See below |
| 8 | Root README links to the Node/TypeScript examples section | ✅ PASS | See below |

---

## AC 1 — `node/README.md` routes to each example

**PASS**

`node/README.md` (PR #13, AAASM-2270) contains a routing table with real links:

```markdown
| [`langchain-js-basic-agent/`](./langchain-js-basic-agent/) | LangChain.js | ... |
| [`openai-node-tool-policy/`](./openai-node-tool-policy/)   | OpenAI Node SDK | ... |
| [`custom-tool-policy/`](./custom-tool-policy/)              | — (none)     | ... |
```

Also includes Quick start, Choosing an example, and Sub-project layout sections.

---

## AC 2 — At least three Node/TypeScript sub-projects exist

**PASS**

Three sub-projects implemented and opened as PRs:

| Sub-project | PR | Ticket |
|---|---|---|
| `node/langchain-js-basic-agent/` | [#7](https://github.com/ai-agent-assembly/agent-assembly-examples/pull/7) | AAASM-2264 |
| `node/openai-node-tool-policy/` | [#9](https://github.com/ai-agent-assembly/agent-assembly-examples/pull/9) | AAASM-2267 |
| `node/custom-tool-policy/` | [#11](https://github.com/ai-agent-assembly/agent-assembly-examples/pull/11) | AAASM-2268 |

---

## AC 3 — Each example has install/run/test scripts

**PASS**

All three `package.json` files include:

```json
"scripts": {
  "build": "tsc --noEmit",
  "start": "node --import tsx/esm src/index.ts",
  "test": "vitest run",
  "typecheck": "tsc --noEmit"
}
```

Verified in:
- `node/langchain-js-basic-agent/package.json`
- `node/openai-node-tool-policy/package.json`
- `node/custom-tool-policy/package.json`

---

## AC 4 — Each example has a deterministic smoke test

**PASS**

All three sub-projects include `tests/smoke.test.ts` using vitest:

| Sub-project | Test file | Test count |
|---|---|---|
| `langchain-js-basic-agent` | `tests/smoke.test.ts` | 5 tests (3 policy + 2 tools) |
| `openai-node-tool-policy` | `tests/smoke.test.ts` | 6 tests (3 policy + 1 defs + 2 tools) |
| `custom-tool-policy` | `tests/smoke.test.ts` | 5 tests (3 policy + 2 tools) |

All tests are deterministic (no network calls, no gateway dependency).

---

## AC 5 — Examples compile under TypeScript strict mode

**PASS**

All three `tsconfig.json` files include:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true
  }
}
```

`pnpm typecheck` (`tsc --noEmit`) passes on all three sub-projects.

---

## AC 6 — Mock/offline mode is the default

**PASS**

- All three `src/index.ts` files call `initAssembly({ mode: "auto" })` without setting `gatewayUrl`
- The SDK resolves to a noop/local gateway when no URL is configured
- No real API keys are required to run `pnpm start` or `pnpm test`
- `.env.example` files have all values commented out

---

## AC 7 — No secrets are committed

**PASS**

- No `.env` files committed (`.gitignore` covers `.env`, `.env.*`)
- Only `.env.example` files committed, with all values commented out
- No API keys, tokens, or credentials in any source file
- Checked: `src/`, `tests/`, `package.json`, `tsconfig.json`

---

## AC 8 — Root README links to the Node/TypeScript examples section

**PASS**

`README.md` (root) already contains (from AAASM-2248):

```markdown
| Use Node.js / TypeScript + LangChain | [`node/`](./node/README.md) |
```

Line 20 of root `README.md` links directly to `./node/README.md`.

---

## Notes

- PRs #7, #9, #11, #13 were open at time of verification (not yet merged into `main`)
- All verification performed against the implementation branch content
- No CI failures detected on any of the four PRs
