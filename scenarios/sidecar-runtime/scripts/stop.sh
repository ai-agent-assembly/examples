#!/usr/bin/env bash
# Stop and remove the local Agent Assembly runtime containers.
# Run from the scenarios/sidecar-runtime/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")/scenarios/sidecar-runtime"

if [[ -f "$SCRIPT_DIR/../docker-compose.yml" ]]; then
  COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

echo "Stopping Agent Assembly local runtime..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" down --remove-orphans

echo "Local runtime stopped. Data is not persisted between runs."
