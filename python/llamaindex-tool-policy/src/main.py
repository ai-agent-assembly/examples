"""
llamaindex-tool-policy: Agent Assembly governance demo with LlamaIndex.

LlamaIndex does not yet have a native Agent Assembly adapter, so this example
shows how to add governance by wrapping each FunctionTool with GovernedToolRunner.
This pattern works for ANY Python callable, not just LlamaIndex.

Run (offline mode, no gateway or API key required):
    uv run python src/main.py
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import GovernedToolRunner, LocalPolicyEngine
from src.tools import _execute_sql_fn, _query_index_fn, _summarize_docs_fn

_DEMO_CALLS: list[tuple[str, Any, dict]] = [
    ("query_index", _query_index_fn, {"query": "what is Agent Assembly?"}),
    ("summarize_docs", _summarize_docs_fn, {"topic": "policy enforcement"}),
    ("execute_sql", _execute_sql_fn, {"sql": "DROP TABLE users; --"}),
]


def _run_governed_call(
    runner: GovernedToolRunner,
    label: str,
    kwargs: dict,
) -> None:
    print(f"  → {label}({kwargs})")
    try:
        result = runner.run(**kwargs)
        print(f"     ✅ ALLOWED  — {result}")
    except ToolExecutionBlockedError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — LlamaIndex Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="llamaindex-demo-agent",
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

        print("Wrapping LlamaIndex tools with GovernedToolRunner...")
        runners = {
            name: GovernedToolRunner(name, fn, policy)
            for name, fn, _ in _DEMO_CALLS
        }
        print("  Tools wrapped: query_index, summarize_docs, execute_sql")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for tool_name, fn, kwargs in _DEMO_CALLS:
            _run_governed_call(runners[tool_name], tool_name, kwargs)

    print("Assembly context shut down.")
    print()
    print("Note: When a native LlamaIndex adapter is available,")
    print("  GovernedToolRunner will no longer be needed — governance")
    print("  will be applied automatically by init_assembly().")


if __name__ == "__main__":
    main()
