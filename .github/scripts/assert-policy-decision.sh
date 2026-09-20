#!/usr/bin/env bash
# Assert the live lane observed a REAL gateway policy decision — an allow AND a
# deny, each on the tool the policy says — rather than a fail-closed deny
# (AAASM-6147 AC 3).
#
# WHY THE DRIVER'S OWN EXIT CODE IS NOT ENOUGH
# --------------------------------------------
# The Python driver fails only when `denied == 0`. So the exact broken topology
# this lane sat in for three iterations — no runtime running, both read_file and
# delete_file denied for `runtime unreachable; failing closed under enforce` —
# satisfied the driver's own check and exited 0. A deny *count* cannot tell
# enforcement apart from an outage, because an outage denies everything.
#
# Two things can tell them apart, and this script checks both:
#
#   1. The deny REASON. `runtime unreachable` / `gateway unreachable` /
#      `failing closed` are the SDK refusing to guess when it cannot reach the
#      decision-maker. `tool denied by policy` is the gateway answering.
#   2. The PAIRING. scenarios/live-core-enforcement/policy.yaml allows read_file
#      and denies delete_file. A run that denies both is answering
#      policy-independently no matter what reason it prints, and a run that
#      allows both means the policy was never loaded.
#
# Python only, deliberately. The Node driver wires the SDK's own no-op gateway
# client (a pass-through posture, by design in that example), so it has no
# decision to assert; the Go driver cannot run at all until AAASM-6150 ships.
set -euo pipefail

OUT="${1:-}"
if [[ -z "${OUT}" ]]; then
  echo "ERROR: usage: assert-policy-decision.sh <captured-driver-output-file>" >&2
  exit 1
fi
if [[ ! -s "${OUT}" ]]; then
  echo "ERROR: '${OUT}' is missing or empty — the driver step produced no output to assert on." >&2
  exit 1
fi

echo "Asserting a real policy decision in ${OUT} ..."

# 1. No fail-closed reason anywhere. This is the check that would have caught the
#    original state, and it is intentionally a hard failure rather than a warning.
if grep -Eqi 'runtime unreachable|gateway unreachable|failing closed|fail-closed' "${OUT}"; then
  echo "ERROR: the run contains a fail-closed deny, so no policy decision was observed." >&2
  echo "       Offending lines:" >&2
  grep -Eni 'runtime unreachable|gateway unreachable|failing closed|fail-closed' "${OUT}" >&2
  echo "       This is a topology failure, not a governance outcome: either aa-runtime" >&2
  echo "       is not bound on the socket the SDK derives from AA_AGENT_ID, or the" >&2
  echo "       gateway it forwards to has no PolicyService. Do NOT satisfy this" >&2
  echo "       assertion by relaxing AA_GATEWAY_FAIL_CLOSED." >&2
  exit 1
fi

# 2. Pair each governed call with the decision the gateway returned for it. The
#    driver prints the call as `→ <tool>(<args>)` and the outcome on the next
#    `[GATEWAY] decision=<status>` line, so the pairing is positional.
decision_for() {
  awk -v want_tool="$1" '
    index($0, want_tool "(") { pending = 1; next }
    pending && /\[GATEWAY\] decision=/ {
      if (match($0, /decision=[a-z]+/)) {
        print substr($0, RSTART + 9, RLENGTH - 9)
      }
      exit
    }
  ' "${OUT}"
}

READ_DECISION="$(decision_for read_file)"
DELETE_DECISION="$(decision_for delete_file)"

echo "  read_file   -> ${READ_DECISION:-<no decision line found>}"
echo "  delete_file -> ${DELETE_DECISION:-<no decision line found>}"

FAILED=0

if [[ "${READ_DECISION}" != "allow" ]]; then
  echo "ERROR: policy.yaml allows read_file, but the gateway returned '${READ_DECISION:-nothing}'." >&2
  echo "       An allowed tool that does not come back allowed means the decision is not" >&2
  echo "       being read from the policy." >&2
  FAILED=1
fi

if [[ "${DELETE_DECISION}" != "deny" ]]; then
  echo "ERROR: policy.yaml denies delete_file, but the gateway returned '${DELETE_DECISION:-nothing}'." >&2
  echo "       This is the direction that matters most: a denied tool coming back allowed" >&2
  echo "       is enforcement failing open." >&2
  FAILED=1
fi

if [[ ${FAILED} -ne 0 ]]; then
  echo "--- captured driver output ---" >&2
  cat "${OUT}" >&2
  exit 1
fi

echo "Real policy decision confirmed: read_file allowed, delete_file denied by policy."
