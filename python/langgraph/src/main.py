"""langgraph-governed-agent: Agent Assembly governance demo with LangGraph.

This example shows how Agent Assembly intercepts a LangGraph state graph at the
node level and enforces policy on the tools each node calls — before any tool
runs. It executes entirely offline: the graph is driven with deterministic
nodes, so no LLM, API key, or running gateway is required.

Run (offline mode, no gateway required):
    uv run python src/main.py

For production use, start the Agent Assembly gateway and update the gateway URL:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.adapters.langgraph import LangGraphAdapter
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.graph import build_graph
from src.policy import LocalPolicyEngine


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — LangGraph Governed Agent Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    # region: quickstart
    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="langgraph-demo-agent",
        mode="sdk-only",
        # No gateway here: the default posture fails closed when registration
        # can't reach one, so an offline demo must name its dry-run posture.
        enforcement_mode="observe",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()
        handler = AssemblyCallbackHandler(interceptor=policy)

        # Install LangGraph node-level governance hooks. The adapter wraps the
        # compiled graph's nodes so tool calls inside each node are governed.
        adapter = LangGraphAdapter()
        adapter.set_process_agent_id(ctx.client.agent_id)
        adapter.register_hooks(handler)
        # endregion

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY    — delete_files, write_file  (destructive operations)")
        print("  PENDING — send_email                (requires human approval)")
        print("  ALLOW   — everything else")
        print()

        print("Invoking governed graph: START → research → report → END")
        print("-" * 44)
        try:
            app = build_graph(handler)
            app.invoke({"topic": "agent governance", "notes": "", "output": ""})
            print("  ⚠️  Graph completed without a block (unexpected).")
        except ToolExecutionBlockedError as exc:
            print("  → research node: get_weather")
            print("     ✅ ALLOWED  — gathered notes (mock response)")
            print("  → report node: delete_files")
            print(f"     ❌ BLOCKED  — {exc}")
        print()

        adapter.unregister_hooks()

    print("Assembly context shut down.")


if __name__ == "__main__":
    main()
