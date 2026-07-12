#!/usr/bin/env bash
# Install and start a real `aasm start --mode local` gateway for the verify-live
# lane, then wait for its /api/v1/health to come up.
#
# SCAFFOLD / rc-gated (AAASM-4475): this is expected to FAIL today. `aasm start
# --mode local` needs `aa-api-server` to serve /api/v1/*, and that binary is not
# yet shipped by the agent-assembly release pipeline (AAASM-4449). The live jobs
# that call this script are `continue-on-error: true` for exactly that reason.
# When AAASM-4449 lands, this script should install a real, working aasm.
set -euo pipefail

AA_API_BASE="${AA_API_BASE:-http://127.0.0.1:7700}"

echo "Installing the aasm CLI (canonical Homebrew tap)..."
# The tap ships the aa-cli + aa-gateway binaries. Note: it does NOT yet ship
# aa-api-server (AAASM-4449), so the REST surface this lane asserts against is
# not served today — hence the quarantine.
brew install ai-agent-assembly/tap/aasm

echo "Starting the local gateway (aasm start --mode local)..."
aasm start --mode local &
echo $! > /tmp/aasm-live.pid

echo "Waiting for the gateway REST surface at ${AA_API_BASE}/api/v1/health ..."
MAX_WAIT=120
ELAPSED=0
until curl -fsS -o /dev/null "${AA_API_BASE}/api/v1/health" 2>/dev/null || [[ $ELAPSED -ge $MAX_WAIT ]]; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [[ $ELAPSED -ge $MAX_WAIT ]]; then
  echo "ERROR: aasm gateway did not become healthy within ${MAX_WAIT}s." >&2
  echo "       This is the expected rc-gated failure until AAASM-4449 ships aa-api-server." >&2
  exit 1
fi

echo "Gateway is healthy."
