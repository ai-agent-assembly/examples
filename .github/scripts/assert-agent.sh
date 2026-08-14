#!/usr/bin/env bash
# Assert that a given agent id is registered and visible in the gateway's
# /api/v1/agents REST surface — the real signal this lane exists to check
# (not merely "the driver process didn't crash").
#
# Usage: assert-agent.sh <agent-id>
set -euo pipefail

AGENT_ID="${1:?usage: assert-agent.sh <agent-id>}"
# 7391, not 7700. `aasm start --mode local` embeds the API on the CLI's own
# --port, which defaults to 7391; 7700 is the default for the STANDALONE
# aa-api-server binary, which this lane downloads but never runs directly. The
# probe polled 7700 for the full 120 s while the gateway was healthy on 7391
# within ~200 ms, and the timeout was then reported as the rc-gate (AAASM-5675).
AA_API_BASE="${AA_API_BASE:-http://127.0.0.1:7391}"

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
