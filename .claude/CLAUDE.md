# CLAUDE.md — examples

Guidance for Claude Code (and humans) working in this repository. This file holds
**repo-specific** context only; universal engineering policy lives in the global
config. When a fact here duplicates a sub-project's `README.md`, `pyproject.toml`,
`package.json`, or a CI workflow, treat those as the source of truth and update
them, not just this file.

Org-wide baseline: https://github.com/ai-agent-assembly/.github/blob/main/CLAUDE.md (org-universal conventions this file doesn't repeat).

## What this repo is

The **runnable example gallery** for AI Agent Assembly — the product that enforces
governance on AI agents. Every sub-directory is a small, self-contained governance
demo that wires a real agent framework (or a bare SDK) into Agent Assembly and
shows a tool call being allowed, denied, gated for approval, audited, or
budget-capped. The core runtime, the SDKs, and the docs hub live in **separate
repos**; this one is the runnable companion you point evaluators at.

### Layout (each leaf is an independent project — no shared build at the root)

| Tree | Contents |
|---|---|
| `python/<example>/` | One `pyproject.toml`-based project each (uv): `langchain-basic-agent`, `crewai-research-crew`, `langgraph`, `pydantic-ai`, `google-adk`, `openai-agents-sdk`, `llamaindex-tool-policy`, `langchain-research-agent`, `custom-tool-policy` |
| `node/<example>/` | One `package.json` (pnpm + TS) each: `langchain-js-basic-agent`, `vercel-ai`, `langgraph-js`, `mastra`, `openai-node-tool-policy`, `custom-tool-policy` |
| `go/<example>/` | One `go.mod` each: `basic-agent`, `tool-policy`, `langchaingo`, `cli-runtime-integration` |
| `scenarios/<scenario>/` | Cross-language runtime demos: `policy-enforcement`, `approval-gates`, `audit-trace`, `budget-limits`, `sidecar-runtime` |
| `docs/` | `concepts.md`, `choosing-an-example.md` (plain Markdown, no site generator) |

There is **no top-level build, lockfile, or workspace**. `cd` into the leaf
sub-project you are touching and run its own commands.

## The mock vs `live` split (read this before touching deps or CI)

Every framework example runs **two ways**, and the distinction is the most
important thing to understand about this repo:

- **`--mock` (the default, what CI runs):** the governance flow is exercised
  **offline** by replaying a scripted tool/delegation trajectory. It needs **none**
  of the heavy agent-framework dependencies — only `agent-assembly` (the SDK) and
  the test deps.
- **`live`:** drives the real framework (a real CrewAI crew, a real LangChain ReAct
  loop, etc.) and usually needs an LLM provider key.

The heavy framework deps therefore sit under an **optional `live` extra**, not in
the base dependency set:

```toml
# python/crewai-research-crew/pyproject.toml
[project.optional-dependencies]
live = ["crewai>=1.14.7"]   # pulls chromadb + a large native tree — live only
dev  = ["pytest>=8.0.0", "pytest-mock>=3.14.0"]
```

CI installs **`uv sync --extra dev`** (not `--extra live`), so the slow,
native-heavy transitive deps (e.g. **chromadb** via `crewai`) are **never installed
in CI**. Keep it that way: a new framework's runtime dependency belongs under
`live`, with the `--mock` path importing it lazily (or not at all) so the smoke
test passes with only `dev` installed. Node examples have no live/mock extra split
— `pnpm install` + `pnpm test` runs the offline smoke path directly.

## Build, test, lint (per sub-project)

```bash
# Python example (uv)
cd python/<example>
uv sync --extra dev            # CI install — NOT --extra live
uv run pytest tests/ -v
uv run python src/main.py --mock   # offline demo run

# Node / TypeScript example (pnpm)
cd node/<example>
pnpm install
pnpm typecheck                 # tsc --noEmit
pnpm test                      # vitest run

# Go example
cd go/<example>
go test ./...

# Scenario smoke runs (no framework deps; offline by default)
python scenarios/<scenario>/python/agent.py
node   scenarios/<scenario>/node/agent.js
```

- `scenarios/policy-enforcement` and `scenarios/approval-gates` have full
  `python/` (uv) **and** `node/` (pnpm) projects with test suites; the lighter
  scenarios ship single-file `agent.py` / `agent.js` smoke runs.
- If a scenario ever ships a **standalone Docusaurus** site (none exist today),
  install it with `pnpm install --ignore-workspace` — it is not part of any pnpm
  workspace and a bare `pnpm install` will mis-resolve it.

## CI

`verify-python`, `verify-node`, `verify-go`, and `verify-scenarios` workflows run
per-example on each PR, gated by `on.pull_request.paths` (e.g. `python/**`) so a
change only triggers the relevant ecosystem. Each runs the **`--mock` / offline**
path — install with the `dev` extra only, never `live`. `verify-scenarios` has a
preflight that detects which scenario directories are present and skips the rest.
Mirror these locally before opening a PR; don't add a `live`-extra install to CI.

## Repo-specific gotchas

- **Default branch is `master`.** A `main` branch also exists but is **stale**
  (`origin/HEAD` may still point at it) — **never** target or merge into `main`.
  All branches and PRs base on `master`.
- **Canonical remote** points at `ai-agent-assembly/examples` — here
  that is **`origin`** (unlike the core monorepo, where it's `remote`). Confirm with
  `git remote -v`; scope changes against `<canonical>/master`.
- **npm dependency fixes:** pin with `^` or a precise version (e.g. `^25.9.3`,
  `0.0.1-beta.3`), **never a bare `>=`** — a bare floor lets Dependabot/resolvers
  drag in a major bump and silently break an example.
- **No secrets, ever.** Config that needs keys ships a `.env.example` only; `.env`
  is gitignored. The `--mock` path needs no keys at all.

## Project policy

- **JIRA:** project AAASM; set **Component** to `ai-agent-assembly/examples`;
  Team (`customfield_10001`) = **Pioneer**. Epic → Story → Subtask (one Subtask ≈
  one commit) + a `Verify …` subtask per Story.
- **Self-hosted deployment is out of scope** product-wide — don't add
  Helm/Terraform/air-gapped examples even if a framework supports them.
- **The Protocol Specification stays in the `agent-assembly` monorepo** — this repo
  is examples only; don't reproduce spec or policy semantics here.

## Documentation conventions — document the WHY, not the WHAT

Comments and docstrings exist to capture intent the code cannot: rationale,
constraints, and the non-obvious governance decision the example is meant to teach.
Restating what the code already says is noise that rots out of sync — avoid it.

- **Python module / package docstrings:** yes — what governance behavior the
  example demonstrates, and crucially **how the `--mock` path differs from `live`**
  (what is replayed vs. really executed). A reader should grasp the demo's point
  without running it.
- **JS/TS module + public-API JSDoc:** yes — on exported wrappers (`withAssembly`,
  tool factories): the contract, the allow/deny/approval outcome, and any offline
  fallback behavior.
- **Why-comments (`#` / `//`):** for the deliberately surprising bits — why a dep is
  under the `live` extra, why a version is pinned with `^`/precise not `>=`, why the
  mock trajectory is scripted the way it is, why `ASSEMBLY_GATEWAY_URL` is left unset
  to exercise the offline path.
- **Skip:** per-variable comments, getters, and anything that merely restates a
  signature or an obvious line of code.
- **Bigger cross-example decisions → an ADR or `docs/concepts.md`**, not scattered
  comments; link the example back to it rather than re-explaining concepts inline.

> Net: a new contributor (human or LLM) should read an example's module docstring
> and understand *what governance behavior it proves and why it's wired this way*
> without reverse-engineering it. If a comment only says *what*, delete it.
