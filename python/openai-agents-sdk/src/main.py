"""
openai-agents-sdk: Agent Assembly governance demo with OpenAI Agents SDK.

This example shows how Agent Assembly intercepts OpenAI Agents tool calls
and enforces policy rules — including approval gates — before execution.

Run (offline mode, no API key required):
    uv run python src/main.py

For production use with a real OpenAI API key and gateway:
    OPENAI_API_KEY=sk-... AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \\
    uv run python src/main.py
"""
from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine
from src.tools import delete_record, search_documents, send_message_to_user

_TOOL_FNS = {
    "search_documents": search_documents,
    "send_message_to_user": send_message_to_user,
    "delete_record": delete_record,
}

_DEMO_CALLS: list[tuple[str, str]] = [
    ("search_documents", '{"query": "agent governance best practices"}'),
    ("send_message_to_user", '{"user_id": "u-001", "message": "Your report is ready."}'),
    ("delete_record", '{"record_id": "rec-7829"}'),
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
        fn = _TOOL_FNS[tool_name]
        import json
        result = fn(**json.loads(input_str))
        print(f"     ✅ ALLOWED  — {result}")
    except ToolExecutionBlockedError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — OpenAI Agents SDK Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="openai-agents-demo",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()
        handler = AssemblyCallbackHandler(interceptor=policy)

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY      — delete_record, drop_table  (destructive data ops)")
        print("  APPROVAL  — send_message_to_user, trigger_payment")
        print("  ALLOW     — everything else")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for tool_name, input_str in _DEMO_CALLS:
            _run_governed_call(handler, tool_name, input_str)

    print("Assembly context shut down.")

    print()
    print("Real OpenAI Agents SDK integration:")
    print("  When openai.agents.FunctionTool is used, Agent Assembly's")
    print("  OpenAIAgentsPatch intercepts tool calls at the framework level.")
    print("  See: https://github.com/AI-agent-assembly/python-sdk")


if __name__ == "__main__":
    main()
