# Contributing

Thanks for helping improve the Agent Assembly examples. This guide covers the
one repo-wide invariant that every contribution has to preserve: SDK version
metadata across the example sub-projects is generated, not hand-maintained.

## Example SDK metadata is generated

Every example under `python/`, `node/`, `go/`, and `scenarios/` advertises the
Agent Assembly SDK version it pins in two places: its manifest
(`pyproject.toml`, `package.json`, or `go.mod`) and its `README.md`. Keeping
those two in sync by hand across 20+ examples is how drift is born, so this
repo owns the pattern with a single source of truth plus a generator plus a
CI check.

### Source of truth

`metadata/sdk-versions.yaml` at the repo root pins the currently-shipped SDK
version for each of the three language ecosystems along with the install
commands used in the READMEs.

### Regenerating after an SDK bump

When a new Agent Assembly SDK release lands and you want the examples to
advertise it:

1. Edit `metadata/sdk-versions.yaml` — update the `version` field for the
   affected language(s). Do not edit any manifest or README by hand.
2. Run the generator from the repo root:

   ```bash
   python scripts/generate_example_metadata.py
   ```

3. Commit the resulting manifest + README changes together with the SoT
   change.

The generator is idempotent: running it twice produces no diff. It uses only
the Python standard library, so no virtualenv or pip install is required.

### Bounded README blocks

Each affected README carries a generated block bounded by:

```markdown
<!-- BEGIN GENERATED: sdk-install -->
...
<!-- END GENERATED: sdk-install -->
```

Never edit content between those markers by hand — it will be overwritten on
the next generator run. Content outside the block (prose about what the
example demonstrates, expected output, troubleshooting) is entirely yours to
edit.

### CI drift check

`.github/workflows/example-metadata-check.yml` runs the generator on every
PR that touches a manifest, README, the SoT, or the generator itself, and
fails the build if the run produces a diff. If that check fails on your PR,
run the generator locally and commit the result.

### What is out of scope for the generator

- **Historical / provenance text** — statements like "this example was
  written against 0.0.1-rc.3" are literal and must not be rewritten.
- **Example runtime code** — the generator only touches manifest pins and
  the sdk-install README block.
- **New examples** — the generator picks up new sub-projects automatically
  based on directory structure (any `python/<name>/pyproject.toml`,
  `node/<name>/package.json` pinning `@agent-assembly/sdk`, or
  `go/<name>/go.mod` pinning `github.com/ai-agent-assembly/go-sdk` is in
  scope). No configuration is needed.
