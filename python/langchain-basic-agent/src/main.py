"""
langchain-basic-agent: Agent Assembly governance demo with LangChain.

This example shows how Agent Assembly intercepts LangChain tool calls and
enforces policy rules before any tool is executed.

Run (offline mode, no gateway required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""
from __future__ import annotations

import json
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine
from src.tools import delete_files, get_weather, send_email

_TOOLS = [get_weather, delete_files, send_email]
_DEMO_CALLS: list[tuple[str, str]] = [
    ("get_weather", '{"city": "London"}'),
    ("delete_files", '{"path": "/etc/passwd"}'),
    ("send_email", '{"to": "all@company.com", "subject": "Hello", "body": "World"}'),
]


def _run_governed_call(
    handler: AssemblyCallbackHandler,
    tool_name: str,
    input_str: str,
) -> None:
    print(f"  → {tool_name}({input_str})")
    run_id = uuid4()
    try:
        handler.on_tool_start(
            serialized={"name": tool_name, "type": "tool"},
            input_str=input_str,
            run_id=run_id,
        )
        tool_map = {t.name: t for t in _TOOLS}
        result = tool_map[tool_name].invoke(json.loads(input_str))
        print(f"     ✅ ALLOWED  — {result}")
    except ToolExecutionBlockedError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — LangChain Basic Agent Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    # region: quickstart
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="langchain-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()
        handler = AssemblyCallbackHandler(interceptor=policy)
        # endregion

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY    — delete_files, write_file  (destructive operations)")
        print("  PENDING — send_email                (requires human approval)")
        print("  ALLOW   — everything else")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for tool_name, input_str in _DEMO_CALLS:
            _run_governed_call(handler, tool_name, input_str)

    print("Assembly context shut down.")


if __name__ == "__main__":
    main()
