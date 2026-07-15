#!/usr/bin/env bash
# Stop and remove the local Agent Assembly runtime containers.
# Run from the scenarios/sidecar-runtime/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")"
[[ -f "$COMPOSE_DIR/docker-compose.yml" ]] || {
    echo "Error: docker-compose.yml not found under $COMPOSE_DIR" >&2
    exit 1
}

echo "Stopping Agent Assembly local runtime..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" down --remove-orphans

echo "Local runtime stopped. Data is not persisted between runs."
