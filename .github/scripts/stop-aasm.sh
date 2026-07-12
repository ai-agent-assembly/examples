#!/usr/bin/env bash
# Tear down the local aasm gateway started by start-aasm.sh. Best-effort:
# invoked from an `if: always()` step, so it must never fail the job itself.
set -uo pipefail

# Prefer the CLI's own shutdown if present.
if command -v aasm >/dev/null 2>&1; then
  aasm stop --mode local >/dev/null 2>&1 || true
fi

# Fall back to the pid we recorded at start.
if [[ -f /tmp/aasm-live.pid ]]; then
  kill "$(cat /tmp/aasm-live.pid)" >/dev/null 2>&1 || true
  rm -f /tmp/aasm-live.pid
fi

echo "aasm gateway stopped (best-effort)."
