"""pydantic-ai-governed-agent: Agent Assembly governance demo with Pydantic AI.

This example shows how Agent Assembly intercepts Pydantic AI tool calls and
enforces policy before any tool executes. It runs **fully offline** using
Pydantic AI's ``TestModel``, so no LLM provider key and no running gateway are
required.

Run (offline mode, no gateway required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.pydantic_ai import PydanticAIAdapter
from agent_assembly.exceptions import PolicyViolationError

from src.agent import build_agent
from src.policy import LocalPolicyEngine

_DEMO_CALLS: list[str] = ["get_weather", "delete_records", "send_email"]


async def _run_governed_call(tool_name: str) -> None:
    print(f"  → agent run that calls {tool_name}")
    agent = build_agent(tool_name)
    try:
        await agent.run("please run the task")
        print(f"     ✅ ALLOWED  — {tool_name} executed (mock response)")
    except PolicyViolationError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


async def _run_demo() -> None:
    print("=" * 62)
    print("  Agent Assembly — Pydantic AI Governed Agent Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    # Install our local-policy tool hooks BEFORE init_assembly. The adapter
    # patches Pydantic AI's tool-execution path (`AbstractToolset.call_tool` on
    # >=0.3.0, `Tool._run` on <0.3.0); because the patch is idempotent,
    # registering first makes init_assembly's auto-detection a no-op and keeps
    # the offline `LocalPolicyEngine` wired as the governance interceptor.
    adapter = PydanticAIAdapter()
    adapter.set_process_agent_id("pydantic-ai-demo-agent")
    adapter.register_hooks(LocalPolicyEngine())

    try:
        with init_assembly(
            gateway_url=gateway_url,
            api_key=api_key,
            agent_id="pydantic-ai-demo-agent",
            mode="sdk-only",
        ) as ctx:
            print(f"  Agent:    {ctx.client.agent_id}")
            print(f"  Gateway:  {ctx.client.gateway_url}")
            print(f"  Mode:     {ctx.network_mode} (offline demo)")
            print()

            print("Policy rules (local simulation of gateway policy):")
            print("  DENY    — delete_records, write_file  (destructive operations)")
            print("  PENDING — send_email                  (requires human approval)")
            print("  ALLOW   — everything else")
            print()

            print("Running governed tool calls (driven offline by TestModel):")
            print("-" * 44)
            for tool_name in _DEMO_CALLS:
                await _run_governed_call(tool_name)
    finally:
        adapter.unregister_hooks()

    print("Assembly context shut down.")


def main() -> None:
    asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
