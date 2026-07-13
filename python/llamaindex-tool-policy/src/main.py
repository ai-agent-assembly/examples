"""llamaindex-tool-policy: Agent Assembly governance demo with LlamaIndex.

LlamaIndex has a native Agent Assembly adapter
(``agent_assembly.adapters.llamaindex``): it monkey-patches the concrete
``FunctionTool.call`` / ``acall`` execution methods, so once the adapter's hooks
are registered, **every** LlamaIndex tool call is governed automatically — the
exact method a ``FunctionAgent`` / ``ReActAgent`` invokes to run a tool. A denied
tool's body never executes; the adapter returns a ``ToolOutput`` flagged
``is_error=True`` carrying a ``[BLOCKED by governance policy]`` message so the
agent loop can react instead of crashing.

This is an **offline** demo: ``LocalPolicyEngine`` simulates the gateway's
allow/deny verdict in-process, so no gateway or API key is required. The tools
and their ``FunctionTool.call`` invocations are real — only the policy decision
is local.

Run:
    uv run python src/main.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.llamaindex import LlamaIndexAdapter, LlamaIndexPatch

from src.policy import LocalPolicyEngine
from src.tools import execute_sql, query_index, summarize_docs

#: The adapter's deny short-circuit marker. The LlamaIndex tool patch returns a
#: ToolOutput carrying this string on a deny rather than raising.
_BLOCKED_MARKER = "[BLOCKED by governance policy]"

_DEMO_CALLS = [
    (query_index, {"query": "what is Agent Assembly?"}),
    (summarize_docs, {"topic": "policy enforcement"}),
    (execute_sql, {"sql": "DROP TABLE users; --"}),
]


def _run_governed_call(tool: object, kwargs: dict[str, str]) -> None:
    name = tool.metadata.get_name()  # type: ignore[attr-defined]
    print(f"  → {name}({kwargs})")
    # The adapter has patched FunctionTool.call, so this single call is governed.
    output = tool.call(**kwargs)  # type: ignore[attr-defined]
    content = str(getattr(output, "content", output))
    if _BLOCKED_MARKER in content:
        print(f"     ❌ BLOCKED  — {content}")
    else:
        print(f"     ✅ ALLOWED  — {content}")
    print()


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — LlamaIndex Tool Policy Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    # region: quickstart
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

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — execute_sql, run_shell_command  (arbitrary execution)")
        print("  ALLOW  — everything else")
        print()

        # Register the native LlamaIndex adapter against the local policy engine.
        # This patches FunctionTool.call so every tool call below is governed
        # automatically — no per-tool wrapper needed.
        #
        # init_assembly() in sdk-only mode already auto-detected LlamaIndex and
        # patched FunctionTool.call against a no-op interceptor (there is no
        # gateway offline). Revert that first so this example's LocalPolicyEngine
        # is the live interceptor; in production init_assembly wires the adapter
        # to the gateway and this manual step is unnecessary.
        print("Registering the native LlamaIndex governance adapter...")
        LlamaIndexPatch(callback_handler=None).revert()
        adapter = LlamaIndexAdapter()
        adapter.register_hooks(LocalPolicyEngine())
        # endregion
        print("  FunctionTool.call / acall are now governed by Agent Assembly.")
        print()

        try:
            print("Running governed tool calls:")
            print("-" * 44)
            for tool, kwargs in _DEMO_CALLS:
                _run_governed_call(tool, kwargs)
        finally:
            adapter.unregister_hooks()

    print("Assembly context shut down.")


if __name__ == "__main__":
    main()
