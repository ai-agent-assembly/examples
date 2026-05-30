# CI Workflows

This directory will contain GitHub Actions workflows that verify the examples in this repository on pull requests and pushes.

## Planned workflows

| Workflow file (coming soon)   | Trigger                      | What it verifies                                        |
|-------------------------------|------------------------------|---------------------------------------------------------|
| `verify-python.yml`           | PR / push affecting `python/`| Python examples install cleanly and run without errors  |
| `verify-node.yml`             | PR / push affecting `node/`  | Node.js examples build and run without errors           |
| `verify-go.yml`               | PR / push affecting `go/`    | Go examples compile and run without errors              |
| `verify-scenarios.yml`        | PR / push affecting `scenarios/` | Scenario examples run end-to-end without errors     |

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
