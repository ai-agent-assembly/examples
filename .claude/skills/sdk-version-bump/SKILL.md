---
name: sdk-version-bump
description: Bump the Agent Assembly SDK version across every example in this repo, correctly and in one pass. Use when a new agent-assembly SDK version has been published (python `agent-assembly`, node `@agent-assembly/sdk`, go `github.com/ai-agent-assembly/go-sdk`) and the examples must be moved onto it — pins, lockfiles, Dockerfiles, generated README blocks, and Prerequisites rows. Encodes the single-source-of-truth flow (`metadata/sdk-versions.yaml` -> `scripts/generate_example_metadata.py`), the per-ecosystem lockfile regen, the orphan-literal audit, and the repo's gotchas. This aligns examples to an ALREADY-published SDK; it does not cut an SDK release.
---

# sdk-version-bump

Runbook for moving every example in this repo onto a new Agent Assembly SDK
version. A bump fans out across 20+ files in three ecosystems — pyproject pins,
`package.json`, `go.mod`, scenario Dockerfiles, pnpm/go/uv lockfiles, the
generated `sdk-install` README block, and the hand-written Prerequisites row
(table **and** bullet). Doing that by hand drifts and re-breaks every release
(AAASM-4451 / 4702 / 4703 / 4717). This skill drives it from the single source of
truth instead, and proves the result with the orphan-literal audit.

**Golden rule:** you never hand-edit a version literal. You edit ONE file
(`metadata/sdk-versions.yaml`), run the generator, regenerate lockfiles, and let
the audit prove nothing was missed.

## When to use

- A new `agent-assembly` SDK version was **published** (to npm / PyPI / the Go
  module proxy) and the examples should advertise and install it.
- The orphan-literal audit (below) is failing in CI and you need to bring a new
  or drifted surface back onto the source of truth.

## When NOT to use

- **Cutting or publishing an SDK release.** That is owned by the SDK repos'
  release runbooks (`node-sdk` / `python-sdk` / `go-sdk`). This skill only aligns
  the examples to a version that is *already live*.
- **Changing which framework or dependency an example uses.** That is ordinary
  example work, not a version bump.

## The single source of truth

`metadata/sdk-versions.yaml` holds one version per ecosystem. Mind the three
distinct formats — they are not interchangeable:

| Ecosystem | Key | Format example |
|---|---|---|
| python | `python.version` | `0.0.1rc5` (PEP 440, no `v`, no dash) |
| node | `node.version` | `0.0.1-rc.5` (SemVer pre-release) |
| go | `go.version` | `v0.0.1-rc.5` (leading `v`) |

`scripts/generate_example_metadata.py` reads this file and rewrites every
version-bearing surface it owns: python/node/go manifests, scenario
`node-agent`/`go-agent` manifests, scenario Dockerfile `agent-assembly==` pins,
the generated `sdk-install` block, the Prerequisites row in both table and
bullet form, and the `agent-assembly` `pip install` pin in the repo's own CI
workflows (`.github/workflows/*.yml`, AAASM-4727 — forced to the exact `==`
form, never a bare `>=` floor). The generator (and the `--check` audit) also own
two more README-prose surfaces (AAASM-4722): a Prerequisites row whose label
cell is the bare backtick **package** name (``| `agent-assembly` SDK | ... |``,
``| `@agent-assembly/sdk` | ... |``) rather than the prose `Agent Assembly
<Lang> SDK` name, and a raw install-hint literal in running prose outside the
generated block (`agent-assembly==<ver>`, `@agent-assembly/sdk@<ver>`). It
**never** bumps versions itself — it aligns everything to this file — and it is
idempotent.

## Runbook

### 1. Verify the target version is actually published (read-only)

Never bump to a version that is not live — the examples would fail to install.
Probe each registry read-only (do **not** install):

```bash
npm view @agent-assembly/sdk@0.0.1-rc.5 version
pip index versions agent-assembly --pre          # look for the target in the list
curl -sf https://proxy.golang.org/github.com/ai-agent-assembly/go-sdk/@v/v0.0.1-rc.5.info
```

Only proceed once all three resolve. Pre-releases need `--pre` on the pip probe.

### 2. Edit the source of truth

Edit the `version` fields in `metadata/sdk-versions.yaml` to the target(s). This
is the only file you edit by hand. Leave the `install_*` templates alone (they
interpolate `{{version}}`).

### 3. Run the generators

```bash
python scripts/generate_example_metadata.py     # rewrites every owned surface
python scripts/extract_snippets.py              # refresh quickstart snippets
```

The first prints the files it rewrote. Dockerfiles are generator-owned — do
**not** hand-edit them.

### 4. Regenerate lockfiles per ecosystem

The generator owns *manifests*, not lockfiles. Regenerate each touched lockfile
in its own sub-project so the lock matches the new pin:

```bash
# node (pnpm) — per node/* and scenarios/*/node-agent that pins the SDK
cd node/<example> && pnpm install --lockfile-only
# go — per go/* and scenarios/*/go-agent
cd go/<example> && go mod tidy
# python (uv) — per python/* and scenarios/*/python that pins the SDK
cd python/<example> && uv lock
```

Gotchas:
- **pnpm 10** can rewrite the lockfile's `overrides`/format even when only the
  pin changed (seen in `99e05b5`); commit the whole regenerated `pnpm-lock.yaml`,
  don't cherry-pick lines.
- Node pins use `^`/precise, **never a bare `>=`** — a bare floor lets a resolver
  drag in a major and silently break the example.
- Python examples install `--extra dev` in CI, never `--extra live`; a bump does
  not change that split.

### 5. Prove it — audit + idempotency

```bash
python scripts/generate_example_metadata.py --check   # orphan-version-literal audit
python scripts/generate_example_metadata.py && git diff --exit-code   # idempotent
```

- `--check` scans every version-bearing surface and exits non-zero, naming
  `file:line`, if any SDK version literal disagrees with the source of truth. On a
  correctly-bumped tree it exits 0. This is the invariant that stops a new stale
  surface from shipping.
- The second command must leave a clean tree — running the generator again
  produces no diff.

If `--check` flags a surface the generator does **not** own, that is a real gap:
either the surface is genuinely new (extend the generator — see AAASM-4719), or
the literal is legitimate historical/provenance text, in which case add the
inline `sdk-version-exempt` marker to that line (documented in the generator's
module docstring). Never silence the audit by hand-editing a literal the
generator should own.

### 6. Commit, branch, PR

- **Branch** off `main` (the default branch since the ADR 0016 migration):
  `<version-or-phase>/<ticket>/<type>/<short_summary>` (e.g.
  `v0.0.1/AAASM-4728/deps/bump_sdk`).
- **Commits** are gitmoji, one logical unit each — e.g. the `sdk-versions.yaml`
  bump, the regenerated manifests/READMEs, and each ecosystem's lockfile regen as
  separate commits. Bisectable; the tree passes the audit at every commit.
- **Canonical remote is `origin`** (this repo, unlike the core monorepo).
- **PR** title `[<ticket>] <emoji> (<scope>): <summary>`, base `main`, body per
  `.github/PULL_REQUEST_TEMPLATE.md`; ≥1 Pioneer-team approval. CI
  (`example-metadata-check.yml`) re-runs the generator, the snippet extractor, the
  `--check` audit, and the generator unit tests, and fails on any drift.

## What CI enforces (so you can't forget a step)

`.github/workflows/example-metadata-check.yml` regenerates metadata + snippets,
runs the orphan-literal audit, and runs `scripts/test_generate_example_metadata.py`
— failing the PR if regeneration produces a diff or the audit finds an orphan. A
green drift-check is the sign the bump is complete and consistent.
