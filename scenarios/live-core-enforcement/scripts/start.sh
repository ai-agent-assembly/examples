#!/usr/bin/env bash
# Bring up the REAL Agent Assembly stack (aa-runtime + bundled gateway) and run
# the live-core enforcement agent against it.
#
# Run from the scenarios/live-core-enforcement/ directory, or anywhere — the
# script resolves the compose file relative to itself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$SCENARIO_DIR/docker-compose.yml"

echo "Starting the real Agent Assembly runtime + gateway..."
docker compose -f "$COMPOSE" up -d --build aa-runtime

echo "Waiting for the runtime/gateway health check..."
MAX_WAIT=120
ELAPSED=0
until docker compose -f "$COMPOSE" ps | grep -q "healthy" || [[ $ELAPSED -ge $MAX_WAIT ]]; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [[ $ELAPSED -ge $MAX_WAIT ]]; then
  echo "ERROR: runtime/gateway did not become healthy within ${MAX_WAIT}s." >&2
  echo "Logs: docker compose -f $COMPOSE logs aa-runtime" >&2
  exit 1
fi

echo ""
echo "Runtime + gateway are ready. Running the live agent..."
echo ""

# Run the agent and stream its output. It exits non-zero if no deny was observed.
docker compose -f "$COMPOSE" up --build --exit-code-from live-agent live-agent

echo ""
echo "Stop the stack when done:"
echo "  bash scripts/stop.sh"
