#!/usr/bin/env bash
# Start the local Agent Assembly runtime via Docker Compose.
# Run from the scenarios/sidecar-runtime/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")/scenarios/sidecar-runtime"

# Allow running from anywhere by resolving relative to this script
if [[ -f "$SCRIPT_DIR/../docker-compose.yml" ]]; then
  COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

echo "Starting Agent Assembly local runtime..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d --build

echo "Waiting for gateway health check..."
MAX_WAIT=60
ELAPSED=0
until docker compose -f "$COMPOSE_DIR/docker-compose.yml" ps | grep -q "healthy" || [ $ELAPSED -ge $MAX_WAIT ]; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "ERROR: Gateway did not become healthy within ${MAX_WAIT}s."
  echo "Run: docker compose -f $COMPOSE_DIR/docker-compose.yml logs assembly-gateway"
  exit 1
fi

echo ""
echo "Local runtime is ready."
echo ""
echo "  Gateway URL:  http://localhost:8080"
echo "  Health check: http://localhost:8080/health"
echo ""
echo "Run an agent example:"
echo "  export ASSEMBLY_GATEWAY_URL=http://localhost:8080"
echo "  python examples/python-agent/agent.py"
echo "  node examples/node-agent/agent.js"
echo ""
echo "Stop when done:"
echo "  bash scripts/stop.sh"
