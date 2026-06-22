"""
haystack-tool-policy: an Agent Assembly governance demo with a real Haystack agent.

Haystack has a **native Agent Assembly adapter** (``HaystackPatch``) that hooks
``haystack.tools.Tool.invoke`` — the single execution chokepoint Haystack 2.x uses
for every tool, including the agentic ``Agent`` -> ``ToolInvoker`` tool-call loop.
This example governs three real ``haystack.tools.Tool`` instances by driving them
through a genuine ``ToolInvoker`` (the component a Haystack ``Agent`` uses to run a
model-chosen tool call) with the native adapter installed against a local policy:

    - ALLOW  query_index, summarize_docs   (safe, read-only)
    - DENY   execute_sql                   (arbitrary execution)

A denied tool's body never runs — the adapter short-circuits ``Tool.invoke`` and
returns a ``[BLOCKED by governance policy]`` message the agent can react to.

Run (offline mode, no gateway or API key required):
    uv run python src/main.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.haystack import HaystackPatch
from haystack.tools import Tool

from src.policy import LocalPolicyEngine
from src.tools import EXECUTED, build_tools

#: The tool calls the demo drives, as (tool_name, arguments). ``execute_sql`` is
#: the one the policy denies.
_DEMO_CALLS: list[tuple[str, dict[str, str]]] = [
    ("query_index", {"query": "what is Agent Assembly?"}),
    ("summarize_docs", {"topic": "policy enforcement"}),
    ("execute_sql", {"sql": "DROP TABLE users; --"}),
]

_BLOCKED_MARKER = "[BLOCKED by governance policy]"


def _invoke_through_tool_invoker(
    tools: list[Tool], tool_name: str, arguments: dict[str, str]
) -> str:
    """Run *tool_name* via a real Haystack ``ToolInvoker`` and return its result.

    Feeds the invoker a hand-built ``ToolCall`` (the shape a chat model would emit)
    so the governed ``Tool.invoke`` is exercised on the genuine agent tool-dispatch
    path, not in isolation — no LLM needed.
    """
    from haystack.components.tools import ToolInvoker
    from haystack.dataclasses import ChatMessage, ToolCall

    invoker = ToolInvoker(tools=tools)
    invoker.warm_up()
    message = ChatMessage.from_assistant(
        tool_calls=[ToolCall(tool_name=tool_name, arguments=arguments)]
    )
    output = invoker.run(messages=[message])
    return str(output["tool_messages"][0].tool_call_results[0].result)


def _print_call(tool_name: str, arguments: dict[str, str], result: str) -> None:
    print(f"  → {tool_name}({arguments})")
    if _BLOCKED_MARKER in result:
        print(f"     ❌ BLOCKED  — {result}")
    else:
        print(f"     ✅ ALLOWED  — {result}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Haystack Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="haystack-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — execute_sql, run_shell_command  (arbitrary execution)")
        print("  ALLOW  — everything else")
        print()

        # init_assembly() has already auto-detected Haystack and patched
        # Tool.invoke — but in offline sdk-only mode it wires a no-op interceptor
        # (there is no live gateway/runtime to answer policy). For this *offline*
        # demo we revert that and re-install the same native adapter against a
        # LocalPolicyEngine so a real allow/deny is visible without a gateway. In
        # production you would instead point init_assembly() at a gateway and let
        # its auto-detected adapter enforce real policy — no manual re-install.
        print("Installing the native Haystack adapter against the demo policy...")
        HaystackPatch(LocalPolicyEngine()).revert()  # drop the auto-applied no-op patch
        patch = HaystackPatch(LocalPolicyEngine())
        installed = patch.apply()
        print(f"  Adapter installed: {installed}")
        print()

        try:
            tools = build_tools()
            print("Running real Haystack tools through a ToolInvoker:")
            print("-" * 44)
            for tool_name, arguments in _DEMO_CALLS:
                result = _invoke_through_tool_invoker(tools, tool_name, arguments)
                _print_call(tool_name, arguments, result)
        finally:
            patch.revert()

    print("Assembly context shut down.")
    print()
    print(f"Tool bodies that actually executed: {EXECUTED}")
    print("  (note: 'execute_sql' is absent — the deny short-circuited it before")
    print("   the tool ran, proving real governance rather than a no-op.)")


if __name__ == "__main__":
    main()
