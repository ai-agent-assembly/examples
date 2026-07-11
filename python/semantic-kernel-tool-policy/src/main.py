"""
semantic-kernel-tool-policy: Agent Assembly governance demo with Semantic Kernel.

Microsoft Semantic Kernel has **no native Agent Assembly adapter** (it is distinct
from the Microsoft Agent Framework, which does), so this example governs its real
``KernelFunction`` objects the framework-agnostic way: each function invocation is
routed through Agent Assembly's callback host, which consults a local policy
*before* ``Kernel.invoke`` reaches the function body. A ``deny`` short-circuits
the function entirely (its body never runs); an ``allow`` runs it and returns its
result.

The demo drives genuine Semantic Kernel native functions — the same
``KernelFunction`` objects a ``Kernel`` invokes — so you can watch governance
allow the safe tools and block the dangerous one with no gateway, API key, or
live LLM.

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

from semantic_kernel.functions import KernelArguments

from agent_assembly import init_assembly
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed_invoke
from src.tools import PLUGIN_NAME, build_kernel

_DEMO_CALLS: list[tuple[str, dict[str, str]]] = [
    ("get_weather", {"city": "London"}),
    ("summarize_docs", {"topic": "policy enforcement"}),
    ("execute_sql", {"sql": "DROP TABLE users; --"}),
]


async def _main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Semantic Kernel Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="semantic-kernel-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()
        kernel = build_kernel()

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — execute_sql, run_shell_command  (arbitrary execution)")
        print("  ALLOW  — everything else")
        print()

        print("Governing real Semantic Kernel KernelFunction.invoke calls.")
        print("Tools governed: get_weather, summarize_docs, execute_sql")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for function_name, arguments in _DEMO_CALLS:
            function = kernel.get_function(PLUGIN_NAME, function_name)
            print(f"  → {function_name}({arguments})")
            try:
                result = await governed_invoke(
                    kernel, function, KernelArguments(**arguments), policy
                )
                print(f"     ✅ ALLOWED  — {result}")
            except ToolExecutionBlockedError as exc:
                print(f"     ❌ BLOCKED  — {exc}")
            print()

    print("Assembly context shut down.")
    print()
    print("Note: in production, init_assembly() wires the live runtime as the")
    print("  interceptor and the gateway answers each allow/deny decision instead")
    print("  of this local demo policy.")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
