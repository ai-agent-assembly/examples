#!/usr/bin/env bash
# Assert that a given agent id is registered and visible in the gateway's
# /api/v1/agents REST surface — the real signal this lane exists to check
# (not merely "the driver process didn't crash").
#
# Usage: assert-agent.sh <agent-id>
set -euo pipefail

AGENT_ID="${1:?usage: assert-agent.sh <agent-id>}"
AA_API_BASE="${AA_API_BASE:-http://127.0.0.1:7700}"

echo "Querying ${AA_API_BASE}/api/v1/agents for '${AGENT_ID}' ..."
AGENTS_JSON="$(curl -fsS "${AA_API_BASE}/api/v1/agents")"

if grep -q -- "${AGENT_ID}" <<<"${AGENTS_JSON}"; then
  echo "OK: agent '${AGENT_ID}' is registered and visible."
else
  echo "FAIL: agent '${AGENT_ID}' is NOT present in /api/v1/agents." >&2
  echo "Response was:" >&2
  echo "${AGENTS_JSON}" >&2
  exit 1
fi
