# CI Workflows

This directory contains the GitHub Actions workflows that verify the examples in this repository on pull requests, pushes, and schedules.

## Workflows in this directory

| Workflow file                 | Trigger                      | What it verifies                                        |
|-------------------------------|------------------------------|-----------------------------------------------------------|
| `verify-python.yml`           | PR / push affecting `python/`| Python examples install cleanly and run without errors  |
| `verify-node.yml`             | PR / push affecting `node/`  | Node.js examples build and run without errors           |
| `verify-go.yml`               | PR / push affecting `go/`    | Go examples compile and run without errors              |
| `verify-scenarios.yml`        | PR / push affecting `scenarios/`; manual dispatch for the real end-to-end run | Scenario examples run end-to-end; the offline smoke lanes are the required per-PR gate, and the real-gateway run is opt-in |
| `verify-all-samples.yml`      | Weekly schedule              | Discovers and runs every sample in the repo, catching drift the per-PR path filters miss |
| `verify-live.yml`             | Daily schedule / manual dispatch | Runs a real (non-mock) SDK driver against a real local gateway, one job per language |
| `example-metadata-check.yml`  | PR affecting SDK version metadata or manifests | SDK version pins and generated README blocks aren't out of sync with `metadata/sdk-versions.yaml` |
| `codeql.yml`                  | PR / push to `master` / weekly schedule | Static security analysis |
| `proof-html.yml`              | Push to `master` / manual dispatch | Rendered HTML/docs links are valid |
| `auto-assign.yml`             | Issue / PR opened            | Auto-assigns an owner |

## Design principles for CI workflows

- Each workflow uses path filters so it only runs when relevant sub-projects change.
- Examples must be runnable with mock or local-only providers — no real API keys required for CI.
- Workflows pin their action versions for reproducibility.
- Secrets are never committed; any required config is documented via `.env.example` and injected as GitHub Actions secrets.

## Adding a workflow for a new example

When you add a sub-project to `python/`, `node/`, `go/`, or `scenarios/`, add or update the corresponding workflow file in this directory. The workflow should:

1. Install the correct language runtime and dependencies.
2. Run the example against a mock or local Agent Assembly gateway.
3. Assert a clean exit code and expected output.

## Back to root

[← Agent Assembly Examples](../../README.md)
