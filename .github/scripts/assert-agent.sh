#!/usr/bin/env bash
# Assert that a given agent id is registered and visible to an authenticated
# operator — the real signal this lane exists to check (not merely "the driver
# process didn't crash").
#
# WHY NOT curl (AAASM-6147)
# -------------------------
# This used to be `curl -fsS "${AA_API_BASE}/api/v1/agents"` with no credential.
# That endpoint is protected — only /api/v1/health is public — so it answered
# `401 {"detail":"Missing Authorization header"}` every run, and the 401 was read
# as the lane's rc-gated transport failure. The endpoint was behaving correctly;
# the lane had simply never authenticated.
#
# The fix is not to bolt a bearer header onto the curl. An operator does not hand
# a token to curl to list their agents; they run the CLI, which reads the
# credential from AASM_API_KEY (`aasm --help` documents preferring the env var
# over the --api-key flag, because a flag leaves the token in argv where `ps` and
# shell history can read it). Going through `aasm agent list` asserts the path a
# real operator uses — the CLI's own auth, URL handling and JSON contract —
# instead of a hand-rolled request that merely resembles it. start-aasm.sh
# provisions the key; see its AASM_API_KEY block.
#
# WHY jq AND NOT grep
# -------------------
# The old check was `grep -q -- "${AGENT_ID}" <<<"${AGENTS_JSON}"`, which passes
# on the id appearing anywhere in the payload: inside another agent's metadata, a
# label, an error string. The surface returns the 32-hex registry hash as `id`
# and the human agent id as `name`, so this asserts structurally on `.name`, with
# `.id` accepted too in case a caller passes the hash.
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

if [[ -z "${AASM_API_KEY:-}" ]]; then
  echo "FAIL: AASM_API_KEY is not set, so this assertion cannot authenticate." >&2
  echo "      start-aasm.sh provisions it and exports it through GITHUB_ENV; run" >&2
  echo "      this after that script, in the same job." >&2
  echo "      Do not work around this by querying the endpoint unauthenticated —" >&2
  echo "      that is the defect AAASM-6147 fixed. It returns 401, not a listing." >&2
  exit 1
fi

echo "Asking the gateway at ${AA_API_BASE} for its agents, as an authenticated operator..."

# `aasm` reads the credential from the environment; it is never passed as a flag.
if ! AGENTS_JSON="$(aasm agent list --api-url "${AA_API_BASE}" --output json 2>/tmp/assert-agent.err)"; then
  echo "FAIL: 'aasm agent list' did not succeed." >&2
  sed 's/^/       /' /tmp/assert-agent.err >&2

  # Separate "the REST surface is gone" from "the query was rejected".
  # /api/v1/health is public, so it answers with no credential; if even that
  # cannot connect then the surface is not listening and the listing was never
  # reached.
  #
  # That happens on a known product defect: aa-api-server serves REST for
  # exactly 30 seconds, then stops listening while the process stays alive and
  # keeps serving gRPC (AAASM-6149). Measured on the released v0.0.1-rc.6 `aasm
  # start --mode local`: authenticated 200 at t=6s, connection failure at t=40s,
  # with only :50051 still bound. Naming it here matters because the symptom
  # otherwise looks like a transport failure in the SDK under test.
  HEALTH="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${AA_API_BASE}/api/v1/health" || true)"
  if [[ "${HEALTH}" == "000" ]]; then
    echo "       The public /api/v1/health probe could not connect either (curl 000)," >&2
    echo "       so the REST surface is not listening; the query never reached it." >&2
    echo "       If the gateway was healthy earlier in this job, this is AAASM-6149:" >&2
    echo "       aa-api-server stops serving REST 30s after start, process still up." >&2
  else
    echo "       /api/v1/health answered HTTP ${HEALTH}, so the REST surface is up and" >&2
    echo "       the listing itself was refused. Check the credential and the error." >&2
  fi
  exit 1
fi

if jq -e --arg id "${AGENT_ID}" \
  '(if type == "array" then . else .items end) | any(.name == $id or .id == $id)' \
  <<<"${AGENTS_JSON}" >/dev/null; then
  echo "OK: agent '${AGENT_ID}' is registered and visible to an authenticated operator."
else
  echo "FAIL: agent '${AGENT_ID}' is NOT in the gateway's agent list." >&2
  echo "      The query itself succeeded, so this is a registration failure, not an" >&2
  echo "      auth or transport one. Agents the gateway does know about:" >&2
  jq -r '(if type == "array" then . else .items end) | map(.name) | join(", ")' \
    <<<"${AGENTS_JSON}" >&2 || echo "      (could not parse the response as agent JSON)" >&2
  exit 1
fi
