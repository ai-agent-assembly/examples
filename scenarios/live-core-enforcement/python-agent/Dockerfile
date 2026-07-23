# Agent container for the live-core enforcement example.
#
# Installs the REAL Agent Assembly Python SDK *with its native extension* so the
# `agent_assembly._core.RuntimeClient` fast path is available — that native
# client is what registers the agent and runs the gRPC/UDS policy check against
# the runtime. The pure-Python wheel alone has no RuntimeClient, so the native
# build (maturin) is required for genuine end-to-end enforcement.
FROM python:3.12-slim

# Build deps for the native (PyO3) extension built by maturin, plus the Rust
# toolchain it needs — installed in one layer. The rustup-init binary is
# fetched over TLS and its checksum verified against rustup's published
# SHA-256 digest before execution, rather than piping curl straight to sh.
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl protobuf-compiler \
    && rm -rf /var/lib/apt/lists/* \
    && case "$TARGETARCH" in \
         amd64) RUST_ARCH=x86_64-unknown-linux-gnu ;; \
         arm64) RUST_ARCH=aarch64-unknown-linux-gnu ;; \
         *) echo "unsupported TARGETARCH: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && curl --proto '=https' --tlsv1.2 -sSfO "https://static.rust-lang.org/rustup/dist/${RUST_ARCH}/rustup-init" \
    && curl --proto '=https' --tlsv1.2 -sSfO "https://static.rust-lang.org/rustup/dist/${RUST_ARCH}/rustup-init.sha256" \
    && sha256sum -c rustup-init.sha256 \
    && chmod +x rustup-init \
    && ./rustup-init -y \
    && rm rustup-init rustup-init.sha256
ENV PATH="/root/.cargo/bin:${PATH}"

# Install maturin (builds the native extension) and the published SDK in one
# layer. For a released wheel with a bundled native binary, `pip install
# agent-assembly` is enough; against a source checkout, build the extension with
# maturin. We install from PyPI here and rely on the platform wheel's native
# layer; if you are developing against a local checkout, mount it and run
# `maturin develop` instead (see README). Versions are pinned and
# `--only-binary=:all:` forces wheel-only installs (both ship wheels for this
# platform), so no arbitrary sdist build script runs during install.
RUN pip install --no-cache-dir --only-binary=:all: "maturin==1.14.1" "agent-assembly==0.0.1rc6"

WORKDIR /app
COPY agent.py /app/agent.py

# Run as a non-root user. The agent only needs to read/write the runtime socket
# on the shared volume; it never needs root.
#
# The uid MUST be 65532 to match the aa-runtime image (distroless `nonroot`,
# uid 65532). The runtime creates its SDK IPC socket
# /tmp/aa-runtime-<agent_id>.sock as mode 0600 owned by 65532 AND rejects any
# connecting peer whose uid != 65532 (peer-uid gating — a deliberate security
# control, not a bug). A mismatched uid can never complete the handshake, so
# every governed call falls back to "runtime unreachable; failing closed under
# enforce" and NO allow path is reachable. Aligning the agent's uid to the
# runtime's is what makes the documented compose enforce out of the box; we do
# NOT loosen the socket to 0666, which would defeat the peer-uid gate.
RUN useradd --create-home --uid 65532 appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "/app/agent.py"]
