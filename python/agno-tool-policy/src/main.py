"""
agno-tool-policy: Agent Assembly governance demo with Agno (formerly Phidata).

Agno has a **native Agent Assembly adapter**. The SDK governs Agno by patching
``agno.tools.function.FunctionCall.execute`` — the single chokepoint every Agno
function-tool call runs through — so every tool an Agno agent invokes passes
through policy *before* its body executes. A ``deny`` short-circuits the tool
entirely (its body never runs); an ``allow`` runs it and records the result.

This demo wires the real Agno adapter (``AgnoPatch``) to a local offline policy
and drives genuine Agno ``@tool`` functions exactly as an Agno ``Agent`` does —
``FunctionCall(...).execute()`` — so you can watch governance allow the safe
tools and block the dangerous one with no gateway, API key, or live LLM.

Run (offline mode, no gateway or API key required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agno.tools.function import Function, FunctionCall

from agent_assembly import init_assembly
from agent_assembly.adapters.agno import AgnoPatch

from src.policy import LocalPolicyEngine
from src.tools import execute_sql, get_weather, summarize_docs

_BLOCKED_MARKER = "[BLOCKED by governance policy]"

_DEMO_CALLS = [
    (get_weather, {"city": "London"}),
    (summarize_docs, {"topic": "policy enforcement"}),
    (execute_sql, {"sql": "DROP TABLE users; --"}),
]


def _run_governed_call(function: Function, arguments: dict[str, str]) -> None:
    """Run a real Agno tool through the patched FunctionCall.execute.

    This is the exact call an Agno ``Agent`` makes to execute a tool — the
    governance hook runs first, so a denied tool returns a failure result and
    its body never executes.
    """
    name = getattr(function, "name", "tool")
    print(f"  → {name}({arguments})")
    result = FunctionCall(function=function, arguments=arguments).execute()
    if result.status == "failure" and _BLOCKED_MARKER in str(result.error):
        print(f"     ❌ BLOCKED  — {result.error}")
    else:
        print(f"     ✅ ALLOWED  — {result.result}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Agno Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="agno-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — execute_sql, run_shell_command  (arbitrary execution)")
        print("  ALLOW  — everything else")
        print()

        # In production init_assembly() auto-detects Agno and wires the live
        # runtime as the interceptor automatically. In this offline sdk-only demo
        # there is no live runtime, so init_assembly() installs a no-op hook; we
        # revert it and re-apply the hook wired to our local policy so the demo
        # shows real allow/deny decisions without a gateway. (The patch is
        # idempotent, so we must revert the no-op hook before installing ours.)
        AgnoPatch(policy).revert()
        patch = AgnoPatch(policy)
        assert patch.apply(), (
            "Agno governance hook did not install — is agno importable?"
        )

        print("Agno governance hook installed on FunctionCall.execute.")
        print("Tools governed: get_weather, summarize_docs, execute_sql")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        try:
            for function, arguments in _DEMO_CALLS:
                _run_governed_call(function, arguments)
        finally:
            patch.revert()

    print("Assembly context shut down.")
    print()
    print("Note: in production, init_assembly() auto-detects Agno and applies")
    print("  this governance automatically — no manual AgnoPatch needed; the")
    print("  live runtime answers the allow/deny decision instead of the demo policy.")


if __name__ == "__main__":
    main()
