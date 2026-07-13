"""google-adk-governed-agent: Agent Assembly governance demo with Google ADK.

Google ADK drives its agent loop against a cloud LLM (Gemini / Vertex AI),
which requires credentials and a network call. This example therefore does not
run a live model — it replays a **scripted tool trajectory** against real ADK
``BaseTool`` instances and exercises the genuine Agent Assembly governance path
on ``run_async``. It runs fully offline with no secrets and no gateway.

Run (offline mode, no gateway required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.exceptions import PolicyViolationError

from src.governance import govern_tool_class, ungovern_tool_class
from src.policy import LocalPolicyEngine
from src.tools import DemoTool, build_tools

_DEMO_CALLS: list[str] = ["get_weather", "delete_records", "send_email"]


def _make_tool_context(agent_id: str) -> SimpleNamespace:
    """Build a minimal ADK ToolContext-shaped object for offline replay."""
    return SimpleNamespace(
        invocation_context=SimpleNamespace(
            assembly_agent_id=agent_id,
            invocation_id="offline-replay",
        ),
    )


async def _run_governed_call(tool: DemoTool, tool_context: SimpleNamespace) -> None:
    print(f"  → {tool.name}(...)")
    try:
        result = await tool.run_async(args={"demo": True}, tool_context=tool_context)
        print(f"     ✅ ALLOWED  — {result}")
    except PolicyViolationError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


async def _run_demo() -> None:
    print("=" * 62)
    print("  Agent Assembly — Google ADK Governed Agent Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    # region: quickstart
    # Govern the concrete demo tool class BEFORE init_assembly so the offline
    # LocalPolicyEngine stays wired as the interceptor (the patch is idempotent).
    govern_tool_class(DemoTool, LocalPolicyEngine())

    try:
        with init_assembly(
            gateway_url=gateway_url,
            api_key=api_key,
            agent_id="google-adk-demo-agent",
            mode="sdk-only",
        ) as ctx:
            # endregion
            print(f"  Agent:    {ctx.client.agent_id}")
            print(f"  Gateway:  {ctx.client.gateway_url}")
            print(f"  Mode:     {ctx.network_mode} (offline demo)")
            print()

            print("Policy rules (local simulation of gateway policy):")
            print("  DENY    — delete_records, write_file  (destructive operations)")
            print("  PENDING — send_email                  (requires human approval)")
            print("  ALLOW   — everything else")
            print()

            print("Replaying scripted tool trajectory (no live LLM):")
            print("-" * 44)
            tools = build_tools()
            tool_context = _make_tool_context(ctx.client.agent_id)
            for tool_name in _DEMO_CALLS:
                await _run_governed_call(tools[tool_name], tool_context)
    finally:
        ungovern_tool_class(DemoTool)

    print("Assembly context shut down.")


def main() -> None:
    asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
