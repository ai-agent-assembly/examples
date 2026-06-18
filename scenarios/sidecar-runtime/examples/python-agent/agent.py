#!/usr/bin/env python3
"""
Sidecar-runtime scenario — Agent Assembly examples

Demonstrates running an AI agent against a local Agent Assembly runtime sidecar.
Connects to the gateway at ASSEMBLY_GATEWAY_URL when set; falls back to an
offline policy when the gateway is not available.

Usage (with local runtime):
    bash scripts/start.sh
    export ASSEMBLY_GATEWAY_URL=http://localhost:8080
    python examples/python-agent/agent.py

Usage (offline, no Docker needed):
    python examples/python-agent/agent.py
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Gateway client — tries the local runtime, falls back to an offline policy
# ---------------------------------------------------------------------------

GATEWAY_URL = os.environ.get("ASSEMBLY_GATEWAY_URL", "").rstrip("/")

_OFFLINE_POLICY: dict[str, tuple[str, str]] = {
    "delete_file":     ("deny",  "destructive operations are blocked by policy"),
    "drop_database":   ("deny",  "destructive operations are blocked by policy"),
}


def _call_gateway(tool: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"tool": tool, "inputs": inputs}).encode()
    req = urllib.request.Request(
        f"{GATEWAY_URL}/v1/tool/call",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _call_offline(tool: str) -> dict[str, Any]:
    decision, reason = _OFFLINE_POLICY.get(tool, ("allow", "permitted by default policy"))
    return {"decision": decision, "reason": reason, "audit_id": None}


def evaluate_tool(tool: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if GATEWAY_URL:
        try:
            return _call_gateway(tool, inputs)
        except OSError as exc:  # URLError subclasses OSError
            print(f"  [WARN] Gateway unreachable ({exc}); falling back to offline policy.")
    return _call_offline(tool)


# ---------------------------------------------------------------------------
# Example agent
# ---------------------------------------------------------------------------


def run() -> None:
    print("=== Agent Assembly — Sidecar Runtime Example ===\n")

    if GATEWAY_URL:
        print(f"Gateway: {GATEWAY_URL}  (connected)\n")
    else:
        print("Gateway: not configured — running in offline mode")
        print("         Set ASSEMBLY_GATEWAY_URL=http://localhost:8080 to connect.")
        print("         See scripts/start.sh to start the local runtime.\n")

    calls: list[tuple[str, dict[str, Any]]] = [
        ("read_file",   {"path": "/data/report.csv"}),
        ("delete_file", {"path": "/data/important.csv"}),
    ]

    mode = "via the local runtime" if GATEWAY_URL else "via offline policy"
    print(f"--- Calling governed tools {mode} ---\n")

    for tool, inputs in calls:
        args_str = ", ".join(f"{k}={v!r}" for k, v in inputs.items())
        print(f"  → {tool}({args_str})")
        response = evaluate_tool(tool, inputs)
        decision = response.get("decision", "unknown")
        reason = response.get("reason", "")
        audit_id = response.get("audit_id")

        if decision == "allow":
            print(f"  [GATEWAY] decision=allow   reason={reason}")
            print("    ✓ allowed\n")
        else:
            print(f"  [GATEWAY] decision=deny    reason={reason}")
            print("    ✗ denied\n")

        if audit_id:
            print(f"  Audit ID: {audit_id}")

    print(f"Total tool calls: {len(calls)}")


if __name__ == "__main__":
    run()
