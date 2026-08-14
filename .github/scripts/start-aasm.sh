#!/usr/bin/env bash
# Install and start a real `aasm start --mode local` gateway for the verify-live
# lane, then wait for its /api/v1/health to come up.
#
# INSTALL PATH — WHY NOT HOMEBREW (AAASM-5675)
# --------------------------------------------
# This script used to run `brew install ai-agent-assembly/tap/aasm`. The live
# jobs run on `ubuntu-latest`, where Homebrew is absent, so that line exited 127
# with "brew: command not found" before the gateway was ever reached. The lane's
# documented rc-gated failure (the health check below timing out) was therefore
# not the failure it was actually producing — a repo-local scripting bug was
# masking the condition the lane exists to report.
#
# The release pipeline publishes per-component Linux tarballs, so the tap is not
# the only route: `aasm-cli-<version>-linux-<arch>.tar.gz` carries `aasm` plus
# `aa-gateway`, and `aasm-api-<version>-linux-<arch>.tar.gz` carries
# `aa-api-server`, the process that serves /api/v1/*. Both are downloaded here
# and checksum-verified against the release's own SHA256SUMS.
#
# NOTE ON AAASM-4449: that ticket is cited elsewhere in this repo as "the release
# pipeline does not yet ship aa-api-server". As of v0.0.1-rc.4 it does —
# `components.json` lists an `api` component for linux-amd64/arm64, and the
# tarball contains an `aa-api-server` binary. Whether `aasm start --mode local`
# brings that surface up is what the health check below measures; this script
# does not assert it in advance.
#
# TWO LOCAL BUGS, NOT ONE. The first fix here (tarballs instead of Homebrew)
# replaced `brew: command not found` with a health probe on the wrong port: the
# gateway binds 7391 and the probe polled 7700 for the full 120 s. The lane was
# red for a second repo-local reason, and both the script and the PR reported it
# as the rc-gate below. Found in review; the port is corrected above.
#
# WHAT IS ACTUALLY RC-GATED: the assertion this lane makes at the end — that an
# agent becomes visible in /api/v1/agents — depends on SDK/transport fixes
# tracked outside this repo (AAASM-4447, AAASM-4467, AAASM-4468, AAASM-4469,
# AAASM-4446). Those are not addressed here.
#
# What this script must NOT do is claim which of those a given red run hit. It
# has twice been wrong about that, in the same direction each time: a local
# defect wearing the label of an external blocker. So it reports what it probed
# and stops there.
set -euo pipefail

# 7391, not 7700. `aasm start --mode local` embeds the API on the CLI's own
# --port, which defaults to 7391; 7700 is the default for the STANDALONE
# aa-api-server binary, which this lane downloads but never runs directly. The
# probe polled 7700 for the full 120 s while the gateway was healthy on 7391
# within ~200 ms, and the timeout was then reported as the rc-gate (AAASM-5675).
AA_API_BASE="${AA_API_BASE:-http://127.0.0.1:7391}"

# Keep aligned with metadata/sdk-versions.yaml, which pins the SDK versions the
# live drivers install. A gateway from a different release than the SDK under
# test would make a failure ambiguous between the two.
AASM_VERSION="${AASM_VERSION:-v0.0.1-rc.6}"
RELEASE_REPO="${AASM_RELEASE_REPO:-ai-agent-assembly/agent-assembly}"
BASE_URL="https://github.com/${RELEASE_REPO}/releases/download/${AASM_VERSION}"

INSTALL_DIR="${RUNNER_TEMP:-/tmp}/aasm-install"
BIN_DIR="${INSTALL_DIR}/bin"
mkdir -p "${BIN_DIR}"

case "$(uname -m)" in
  x86_64 | amd64) ARCH="amd64" ;;
  aarch64 | arm64) ARCH="arm64" ;;
  *)
    echo "ERROR: unsupported architecture '$(uname -m)' — the release publishes linux-amd64 and linux-arm64." >&2
    exit 1
    ;;
esac

CLI_TARBALL="aasm-cli-${AASM_VERSION}-linux-${ARCH}.tar.gz"
API_TARBALL="aasm-api-${AASM_VERSION}-linux-${ARCH}.tar.gz"

echo "Installing the aasm CLI and aa-api-server from ${RELEASE_REPO}@${AASM_VERSION} (linux-${ARCH})..."
pushd "${INSTALL_DIR}" >/dev/null

# --proto '=https' rejects a non-HTTPS URL outright and --proto-redir '=https'
# holds that across the redirect chain, which -L follows (the release download
# URL redirects to objects.githubusercontent.com). Without the second flag a
# redirect could downgrade the transport for a binary this script then executes.
CURL_OPTS=(--fail --silent --show-error --location --proto '=https' --proto-redir '=https' --tlsv1.2 --remote-name)

curl "${CURL_OPTS[@]}" "${BASE_URL}/SHA256SUMS"
curl "${CURL_OPTS[@]}" "${BASE_URL}/${CLI_TARBALL}"
curl "${CURL_OPTS[@]}" "${BASE_URL}/${API_TARBALL}"

# Verify before extracting. --ignore-missing lets one SHA256SUMS cover the whole
# release while this lane downloads two of its assets.
echo "Verifying checksums against the release SHA256SUMS..."
sha256sum --check --ignore-missing SHA256SUMS

tar -xzf "${CLI_TARBALL}" -C "${BIN_DIR}"
tar -xzf "${API_TARBALL}" -C "${BIN_DIR}"
chmod +x "${BIN_DIR}"/*
popd >/dev/null

export PATH="${BIN_DIR}:${PATH}"
# Persist onto PATH for the later steps in this job (the driver run and the
# /api/v1/agents assertion both shell out to `aasm`).
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${BIN_DIR}" >>"${GITHUB_PATH}"
fi

echo "Installed: $(aasm --version 2>&1 || echo 'aasm --version failed')"

echo "Starting the local gateway (aasm start --mode local)..."
aasm start --mode local &
echo $! > /tmp/aasm-live.pid

echo "Waiting for the gateway REST surface at ${AA_API_BASE}/api/v1/health ..."
MAX_WAIT=120
ELAPSED=0
until curl -fsS -o /dev/null "${AA_API_BASE}/api/v1/health" 2>/dev/null || [[ $ELAPSED -ge $MAX_WAIT ]]; do
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [[ $ELAPSED -ge $MAX_WAIT ]]; then
  echo "ERROR: aasm gateway did not become healthy within ${MAX_WAIT}s." >&2
  echo "       Probed: ${AA_API_BASE}/api/v1/health" >&2
  echo "       Read the gateway output above for the address it actually bound." >&2
  # This used to read "This is the rc-gated failure described in verify-live.yml's
  # header." It was not: the probe was on the wrong port, and the script asserted
  # a cause it has no way to determine. A timeout says the probe did not succeed,
  # nothing more — so it now prints what it probed and points at the evidence
  # instead of naming a culprit (AAASM-5675).
  exit 1
fi

echo "Gateway is healthy."
