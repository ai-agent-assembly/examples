"""
autogen-tool-policy: Agent Assembly governance demo with AutoGen (autogen-core).

AutoGen has **no native Agent Assembly adapter**, so this example governs its
real ``autogen_core.tools.FunctionTool`` objects the framework-agnostic way: each
tool invocation is routed through Agent Assembly's callback host, which consults
a local policy *before* ``FunctionTool.run_json`` reaches the tool body. A
``deny`` short-circuits the tool entirely (its body never runs); an ``allow``
runs it and returns its result.

The demo drives genuine AutoGen ``FunctionTool`` objects — the same objects an
AutoGen ``AssistantAgent`` invokes — so you can watch governance allow the safe
tools and block the dangerous one with no gateway, API key, or live LLM.

Run (offline mode, no gateway or API key required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autogen_core.tools import FunctionTool

from agent_assembly import init_assembly
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed_run
from src.tools import execute_sql, get_weather, summarize_docs

_DEMO_CALLS: list[tuple[FunctionTool, dict[str, str]]] = [
    (get_weather, {"city": "London"}),
    (summarize_docs, {"topic": "policy enforcement"}),
    (execute_sql, {"sql": "DROP TABLE users; --"}),
]


async def _run_governed_call(
    tool: FunctionTool, arguments: dict[str, str], policy: LocalPolicyEngine
) -> None:
    """Run a real AutoGen tool through the governed execution path.

    A denied tool raises ``ToolExecutionBlockedError`` before its body runs.
    """
    print(f"  → {tool.name}({arguments})")
    try:
        result = await governed_run(tool, arguments, policy)
        print(f"     ✅ ALLOWED  — {result}")
    except ToolExecutionBlockedError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


async def _main() -> None:
    print("=" * 62)
    print("  Agent Assembly — AutoGen Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="autogen-demo-agent",
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

        print("Governing real AutoGen FunctionTool.run_json calls.")
        print("Tools governed: get_weather, summarize_docs, execute_sql")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for tool, arguments in _DEMO_CALLS:
            await _run_governed_call(tool, arguments, policy)

    print("Assembly context shut down.")
    print()
    print("Note: in production, init_assembly() wires the live runtime as the")
    print("  interceptor and the gateway answers each allow/deny decision instead")
    print("  of this local demo policy.")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
