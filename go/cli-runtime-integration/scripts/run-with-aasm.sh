#!/usr/bin/env bash
# run-with-aasm.sh — start the aasm sidecar then run the cli-runtime-integration example.
#
# Usage:
#   bash scripts/run-with-aasm.sh
#
# Requirements:
#   - aasm must be installed and on PATH
#     Install: brew install agent-assembly/tap/aasm
#              curl -fsSL https://get.agent-assembly.io | sh
#
# The script starts the sidecar in the background, waits for it to become
# healthy, runs the Go example, then shuts the sidecar down on exit.

set -euo pipefail

AASM_PORT="${AASM_PORT:-7878}"
AASM_LOG=".aasm-runtime.log"
WAIT_SECONDS="${WAIT_SECONDS:-5}"

cleanup() {
    if [[ -n "${AASM_PID:-}" ]] && kill -0 "$AASM_PID" 2>/dev/null; then
        echo "[run-with-aasm] stopping sidecar (pid=$AASM_PID)"
        kill "$AASM_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

if ! command -v aasm &>/dev/null; then
    echo "[run-with-aasm] ERROR: aasm binary not found." >&2
    echo "[run-with-aasm] Install: brew install agent-assembly/tap/aasm" >&2
    echo "[run-with-aasm]          curl -fsSL https://get.agent-assembly.io | sh" >&2
    exit 1
fi

echo "[run-with-aasm] starting aasm sidecar on port $AASM_PORT..."
aasm serve --port "$AASM_PORT" >>"$AASM_LOG" 2>&1 &
AASM_PID=$!

# Wait for the sidecar to become ready.
for i in $(seq 1 "$WAIT_SECONDS"); do
    if nc -z 127.0.0.1 "$AASM_PORT" 2>/dev/null; then
        echo "[run-with-aasm] sidecar ready (waited ${i}s)"
        break
    fi
    sleep 1
done

if ! nc -z 127.0.0.1 "$AASM_PORT" 2>/dev/null; then
    echo "[run-with-aasm] ERROR: sidecar did not start within ${WAIT_SECONDS}s — check $AASM_LOG" >&2
    exit 1
fi

echo "[run-with-aasm] running example..."
go run .
