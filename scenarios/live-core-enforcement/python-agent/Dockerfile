# Agent container for the live-core enforcement example.
#
# Installs the REAL Agent Assembly Python SDK *with its native extension* so the
# `agent_assembly._core.RuntimeClient` fast path is available — that native
# client is what registers the agent and runs the gRPC/UDS policy check against
# the runtime. The pure-Python wheel alone has no RuntimeClient, so the native
# build (maturin) is required for genuine end-to-end enforcement.
FROM python:3.12-slim

# Build deps for the native (PyO3) extension built by maturin, plus the Rust
# toolchain it needs — installed in one layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl protobuf-compiler \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install maturin (builds the native extension) and the published SDK in one
# layer. For a released wheel with a bundled native binary, `pip install
# agent-assembly` is enough; against a source checkout, build the extension with
# maturin. We install from PyPI here and rely on the platform wheel's native
# layer; if you are developing against a local checkout, mount it and run
# `maturin develop` instead (see README).
RUN pip install --no-cache-dir maturin "agent-assembly>=0.0.1rc3"

WORKDIR /app
COPY agent.py /app/agent.py

# Run as a non-root user. The agent only needs to read/write the runtime socket
# on the shared volume; it never needs root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "/app/agent.py"]
