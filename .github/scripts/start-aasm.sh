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
# `aa-gateway`, `aasm-api-<version>-linux-<arch>.tar.gz` carries `aa-api-server`
# (the process that serves /api/v1/*), and `aasm-runtime-<version>-linux-<arch>
# .tar.gz` carries `aa-runtime` (the process that binds the IPC socket the SDKs
# query before a tool call). All three are downloaded here and checksum-verified
# against the release's own SHA256SUMS.
#
# NOTE ON AAASM-4449: that ticket is cited elsewhere in this repo as "the release
# pipeline does not yet ship aa-api-server". As of v0.0.1-rc.4 it does —
# `components.json` lists an `api` component for linux-amd64/arm64, and the
# tarball contains an `aa-api-server` binary. Whether `aasm start --mode local`
# brings that surface up is what the health check below measures; this script
# does not assert it in advance.
#
# THREE LOCAL BUGS, NOT ONE. The first fix here (tarballs instead of Homebrew)
# replaced `brew: command not found` with a health probe on the wrong port: the
# gateway binds 7391 and the probe polled 7700 for the full 120 s. The lane was
# red for a second repo-local reason, and both the script and the PR reported it
# as the rc-gate below. Found in review; the port is corrected above.
#
# The third is the one fixed by this change: the gateway was started with no
# operator credential, so the registration assertion queried a protected
# endpoint unauthenticated and got a 401 — see the AASM_API_KEY block below
# (AAASM-6147). Same shape as the first two, a third time: a local setup gap
# wearing an external blocker's label.
#
# WHAT IS ACTUALLY RC-GATED: the assertion this lane makes at the end — that an
# agent becomes visible to an authenticated operator — is blocked for the Go job
# by AAASM-6150 (the published go-sdk links no transport, so `assembly.Init`
# cannot connect). Beyond registration, no job in this topology can observe a
# real policy decision, because nothing shipped binds the runtime IPC socket the
# SDKs query (AAASM-6151). Neither is addressed here; neither is what the 401
# above was.
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
# The `runtime` component, listed in the release's components.json for all four
# darwin/linux × amd64/arm64 targets. It is what binds the runtime IPC socket;
# without it the SDK's pre-execution check has nothing to query and fails closed.
RUNTIME_TARBALL="aasm-runtime-${AASM_VERSION}-linux-${ARCH}.tar.gz"

echo "Installing the aasm CLI, aa-api-server and aa-runtime from ${RELEASE_REPO}@${AASM_VERSION} (linux-${ARCH})..."
pushd "${INSTALL_DIR}" >/dev/null

# --proto '=https' rejects a non-HTTPS URL outright and --proto-redir '=https'
# holds that across the redirect chain, which -L follows (the release download
# URL redirects to objects.githubusercontent.com). Without the second flag a
# redirect could downgrade the transport for a binary this script then executes.
CURL_OPTS=(--fail --silent --show-error --location --proto '=https' --proto-redir '=https' --tlsv1.2 --remote-name)

curl "${CURL_OPTS[@]}" "${BASE_URL}/SHA256SUMS"
curl "${CURL_OPTS[@]}" "${BASE_URL}/${CLI_TARBALL}"
curl "${CURL_OPTS[@]}" "${BASE_URL}/${API_TARBALL}"
curl "${CURL_OPTS[@]}" "${BASE_URL}/${RUNTIME_TARBALL}"

# Verify before extracting. --ignore-missing lets one SHA256SUMS cover the whole
# release while this lane downloads three of its assets.
echo "Verifying checksums against the release SHA256SUMS..."
sha256sum --check --ignore-missing SHA256SUMS

tar -xzf "${CLI_TARBALL}" -C "${BIN_DIR}"
tar -xzf "${API_TARBALL}" -C "${BIN_DIR}"
tar -xzf "${RUNTIME_TARBALL}" -C "${BIN_DIR}"
chmod +x "${BIN_DIR}"/*
popd >/dev/null

export PATH="${BIN_DIR}:${PATH}"
# Persist onto PATH for the later steps in this job (the driver run and the
# /api/v1/agents assertion both shell out to `aasm`).
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${BIN_DIR}" >>"${GITHUB_PATH}"
fi

echo "Installed: $(aasm --version 2>&1 || echo 'aasm --version failed')"

# OPERATOR CREDENTIAL (AAASM-6147)
# --------------------------------
# The protected `/api/v1/*` surface requires `Authorization: Bearer aa_…`; only
# `/api/v1/health` is public, which is why the wait loop below needs no key. The
# lane previously started the gateway with no credential at all, so its
# registration assertion queried /api/v1/agents unauthenticated and got
# `401 {"detail":"Missing Authorization header"}`. The endpoint was behaving
# correctly; the setup had simply never authenticated.
#
# A real operator sets AASM_API_KEY. That is the product's own instruction — with
# the variable unset the server prints "generated admin API key (set AASM_API_KEY
# to reuse)" — and `aasm --help` documents preferring the env var over the
# `--api-key` flag, because a flag puts the bearer token in argv where `ps` and
# shell history can read it. So the lane authenticates the way the product tells
# operators to, and the assertion exercises that path rather than bypassing it.
#
# Generated per run, never stored. With AASM_API_KEY unset the server mints a
# random key and logs only its first 6 characters, which no later step can
# reconstruct — so the key has to be chosen here for the assertion to be able to
# authenticate at all. Generating it per run also keeps any credential-shaped
# string out of the repository and out of repo secrets. The format contract is
# `aa_` followed by exactly 32 hex characters (aa-auth/src/api_key.rs parses and
# rejects anything else), which `openssl rand -hex 16` satisfies.
if [[ -z "${AASM_API_KEY:-}" ]]; then
  AASM_API_KEY="aa_$(openssl rand -hex 16)"
fi
export AASM_API_KEY

# Mask first, then publish: ::add-mask:: redacts the value from this job's log
# before any later step can echo it, and GITHUB_ENV is how the assertion step —
# a separate shell — receives it.
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "::add-mask::${AASM_API_KEY}"
  echo "AASM_API_KEY=${AASM_API_KEY}" >>"${GITHUB_ENV}"
fi

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
