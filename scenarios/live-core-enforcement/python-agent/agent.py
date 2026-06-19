#!/usr/bin/env python3
"""Live-core enforcement example — Agent Assembly examples.

Unlike the other scenarios in this repo, this one is **not** a stand-in. It
imports the *real* published SDK (``agent_assembly``) and exercises the genuine
end-to-end governance path described in ADR 0004:

    your agent
        │  init_assembly(...)            ← registers the agent on startup
        │  client.check_tool_start(...)  ← pre-execution policy check
        ▼
    Agent Assembly SDK (agent_assembly)
        │  native _core / aa-sdk-client (gRPC over a Unix domain socket)
        ▼
    aa-runtime sidecar  ──gRPC──►  aa-gateway (the policy authority)

The SDK's native ``RuntimeClient`` connects to the runtime UDS at
``/tmp/aa-runtime-<agent_id>.sock`` (overridable via ``AA_RUNTIME_SOCKET``),
registers the agent, and routes every ``check_tool_start`` through the runtime's
``query_policy`` to the gateway. A policy ``deny`` therefore *actually blocks*
the tool before it runs — there is no HTTP shim and no offline fallback here.

Running this requires a real runtime + gateway. Bring them up with the bundled
compose stack (see the scenario README), which loads ``policy.yaml`` into a real
``aa-gateway``. The policy in this example allows ``read_file`` and denies
``delete_file``; you should see the first call permitted and the second blocked.

Usage:
    # 1. start the real stack (real aa-runtime + aa-gateway + sample policy)
    bash scripts/start.sh

    # 2. run this agent against it (native SDK build required — see README)
    export AA_AGENT_ID=live-core-demo-agent
    export AA_RUNTIME_SOCKET=/tmp/aa-runtime-live-core-demo-agent.sock
    python python-agent/agent.py
"""
from __future__ import annotations

import json
import os
import sys

# The real SDK. If these imports fail, the package is not installed — there is no
# stand-in in this scenario by design (that is what sidecar-runtime covers).
from agent_assembly import init_assembly
from agent_assembly.core.runtime_interceptor import (
    RuntimeQueryInterceptor,
    _resolve_runtime_socket_path,
    connect_runtime_client,
)

AGENT_ID = os.environ.get("AA_AGENT_ID", "live-core-demo-agent")

# The native fast path connects to the runtime UDS. init_assembly also resolves
# a gateway_url for the SDK's non-native routes; against the local stack the
# runtime owns the gRPC/UDS transport, so this only needs to be set.
GATEWAY_URL = os.environ.get("AA_GATEWAY_URL", "http://localhost:7391")

# Tool calls this agent attempts. With policy.yaml loaded into the gateway,
# read_file is allowed and delete_file is denied.
_CALLS: list[tuple[str, dict[str, object]]] = [
    ("read_file", {"path": "/data/report.csv"}),
    ("delete_file", {"path": "/data/important.csv"}),
]


def _check(interceptor: RuntimeQueryInterceptor, tool: str, inputs: dict[str, object]) -> dict[str, str]:
    """Run a governed pre-execution check through the SDK's runtime path.

    ``check_tool_start`` is the adapter-contract surface the production
    ``RuntimeQueryInterceptor`` exposes: it forwards the call to the runtime's
    native ``query_policy`` (gRPC/UDS) and returns
    ``{"status": "allow" | "deny" | "pending", "reason": ...}``. This is the
    exact interceptor the SDK's framework adapters use to block a denied tool.
    """
    return interceptor.check_tool_start(
        serialized={"name": tool},
        input_str=json.dumps(inputs),
    )


def run() -> int:
    print("=== Agent Assembly — Live-Core Enforcement Example ===\n")
    print(f"Agent ID:   {AGENT_ID}")
    print(f"Gateway:    {GATEWAY_URL}")
    # Resolve the runtime socket display value through the SDK's own resolver
    # (AA_RUNTIME_SOCKET > per-agent default) rather than hardcoding a path.
    print(f"Runtime:    {_resolve_runtime_socket_path(AGENT_ID)}\n")

    # init_assembly registers the agent with the real gateway over the native
    # runtime client and wires the pre-execution check. enforce = a deny blocks.
    with init_assembly(
        gateway_url=GATEWAY_URL,
        agent_id=AGENT_ID,
        enforcement_mode="enforce",
    ) as ctx:
        print(f"Registered agent '{AGENT_ID}' (network mode: {ctx.network_mode}).\n")

        # The governed pre-execution check goes through the production
        # RuntimeQueryInterceptor, wrapping a native runtime client connected to
        # the live runtime UDS — the same path the SDK's framework adapters use.
        runtime_client = connect_runtime_client(AGENT_ID)
        if runtime_client is None:
            print(
                "ERROR: no native runtime client — the native SDK extension is "
                "missing or the runtime socket is unreachable. This scenario "
                "requires the native build + a live runtime (see README).",
                file=sys.stderr,
            )
            return 1
        interceptor = RuntimeQueryInterceptor(
            ctx.client, runtime_client, AGENT_ID, enforce=True
        )

        print("--- Calling governed tools via the SDK -> live runtime -> gateway ---\n")

        denied = 0
        for tool, inputs in _CALLS:
            args = ", ".join(f"{k}={v!r}" for k, v in inputs.items())
            print(f"  → {tool}({args})")
            result = _check(interceptor, tool, inputs)
            status = str(result.get("status", "unknown")).lower()
            reason = result.get("reason", "")
            audit_id = result.get("audit_id") or result.get("audit_event_id")

            if status == "allow":
                print(f"  [GATEWAY] decision=allow   {('reason=' + reason) if reason else ''}".rstrip())
                print("    ✓ allowed — tool would execute\n")
            else:
                denied += 1
                print(f"  [GATEWAY] decision={status}    reason={reason}")
                print("    ✗ blocked — tool did NOT execute\n")
            if audit_id:
                print(f"    Audit ID: {audit_id}\n")

        print(f"Total tool calls: {len(_CALLS)}  |  blocked by policy: {denied}")

        if denied == 0:
            print(
                "\nWARNING: expected at least one deny. Is policy.yaml loaded into "
                "the gateway and is the native SDK build connected to the runtime?",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
