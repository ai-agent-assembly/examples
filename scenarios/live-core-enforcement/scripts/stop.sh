#!/usr/bin/env bash
# Stop and remove the real Agent Assembly stack and its socket volume.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE="$SCENARIO_DIR/docker-compose.yml"

echo "Stopping the Agent Assembly stack..."
docker compose -f "$COMPOSE" down -v --remove-orphans

echo "Stack stopped. The socket volume was removed; nothing is persisted."
