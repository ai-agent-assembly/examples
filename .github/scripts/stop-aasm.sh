#!/usr/bin/env bash
# Tear down the local aa-runtime and aasm gateway started by start-aasm.sh.
# Best-effort: invoked from an `if: always()` step, so it must never fail the job
# itself.
set -uo pipefail

# Runtime first, gateway second: the runtime holds an op-control stream to the
# gateway, so stopping it the other way round makes it log connection errors on
# the way down that read like a failure.
#
# The socket is removed explicitly. A stale /tmp/aa-runtime-<id>.sock left behind
# by a killed runtime is worse than none at all: the SDK would find a path that
# exists, connect to nothing, and report it as an enforcement outcome.
if [[ -f /tmp/aa-runtime-live.pid ]]; then
  kill "$(cat /tmp/aa-runtime-live.pid)" >/dev/null 2>&1 || true
  rm -f /tmp/aa-runtime-live.pid
fi
rm -f /tmp/aa-runtime-*.sock

# Prefer the CLI's own shutdown if present.
if command -v aasm >/dev/null 2>&1; then
  aasm stop --mode local >/dev/null 2>&1 || true
fi

# Fall back to the pid we recorded at start.
if [[ -f /tmp/aasm-live.pid ]]; then
  kill "$(cat /tmp/aasm-live.pid)" >/dev/null 2>&1 || true
  rm -f /tmp/aasm-live.pid
fi

echo "aa-runtime and aasm gateway stopped (best-effort)."
