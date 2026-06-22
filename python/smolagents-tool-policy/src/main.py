"""
smolagents-tool-policy: an Agent Assembly governance demo with Smolagents.

Smolagents has a **native** Agent Assembly adapter, so governance is automatic:
``init_assembly()`` detects smolagents and installs the hook on
``smolagents.tools.Tool.__call__`` (the chokepoint every tool execution flows
through). Every real ``smolagents.Tool`` invocation then passes through policy
*before* its ``forward`` body runs — a denied tool is short-circuited with the
``[BLOCKED by governance policy]`` message; an allowed tool runs and is recorded.

This demo invokes the real governed tools directly (the same call a smolagents
agent makes to execute a tool) rather than spinning up an LLM agent loop, so it
runs fully **offline** — no gateway, no API key, no model. The governance path
exercised is identical to a live agent; only the model that *decides* which tool
to call is absent.

Run (offline demo, no gateway or API key required):
    uv run python src/main.py
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.smolagents import SmolagentsPatch

from src.policy import LocalPolicyEngine
from src.tools import build_tools

_BLOCKED_MARKER = "[BLOCKED by governance policy]"

#: (tool name, kwargs) the demo drives — two allowed, one denied.
_DEMO_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("search_docs", {"query": "what is Agent Assembly?"}),
    ("summarize", {"topic": "policy enforcement"}),
    ("run_shell_command", {"command": "rm -rf /var/data"}),
]


def _run_governed_call(tool: Any, label: str, kwargs: dict[str, Any]) -> None:
    print(f"  → {label}({kwargs})")
    result = tool(**kwargs)
    if isinstance(result, str) and _BLOCKED_MARKER in result:
        print(f"     ❌ BLOCKED  — {result}")
    else:
        print(f"     ✅ ALLOWED  — {result}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Smolagents Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    # Govern the real smolagents Tool class with the local offline policy BEFORE
    # init_assembly(): init_assembly() auto-detects smolagents and would otherwise
    # install the hook with its default no-op interceptor first, and the patch is
    # idempotent (it won't re-wrap). Applying our policy patch first means our
    # decisions win; init's auto-detect then finds Tool.__call__ already governed
    # and leaves it. In production init_assembly() wires the real gateway
    # interceptor here automatically — no local policy needed.
    policy = LocalPolicyEngine()
    patch = SmolagentsPatch(policy)
    patch.apply()

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="smolagents-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — run_shell_command, delete_records  (destructive ops)")
        print("  ALLOW  — everything else")
        print()

        try:
            tools = build_tools()
            print("Governing real smolagents.Tool instances via Tool.__call__:")
            print(f"  Tools: {', '.join(tools)}")
            print()

            print("Running governed tool calls:")
            print("-" * 44)
            for tool_name, kwargs in _DEMO_CALLS:
                _run_governed_call(tools[tool_name], tool_name, kwargs)
        finally:
            patch.revert()

    print("Assembly context shut down.")
    print()
    print("Every call above ran through the real smolagents adapter")
    print("(Tool.__call__): the denied tool's forward() never executed.")


if __name__ == "__main__":
    main()
