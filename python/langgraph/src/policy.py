"""Local offline policy engine for the langgraph-governed-agent example.

In production, Agent Assembly's gateway enforces policy server-side. This
module simulates that governance layer locally so the demo runs without a
running gateway.

The ``LangGraphAdapter`` installs node-level hooks (``on_graph_node_start`` /
``on_graph_node_end``) and threads tool calls through LangChain's
``AssemblyCallbackHandler``, which reads the allow / deny / pending decisions
returned by ``check_tool_start`` below.

Production setup:
    ctx = init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent")
    # Policy rules are defined in the gateway; the SDK enforces them automatically.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

DENIED_TOOLS: frozenset[str] = frozenset({
    "delete_files",
    "write_file",
})

PENDING_TOOLS: frozenset[str] = frozenset({
    "send_email",
})


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    Returns allow / deny / pending decisions that mirror the gateway wire
    format. The ``AssemblyCallbackHandler`` reads these decisions and raises
    ``ToolExecutionBlockedError`` for deny / unresolved-pending outcomes.

    The node-level ``on_graph_node_start`` / ``on_graph_node_end`` hooks record
    graph topology; in offline mode they simply print the traversal.
    """

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule "
                    "'deny_destructive_operations'."
                ),
            }
        if tool_name in PENDING_TOOLS:
            return {
                "status": "pending",
                "reason": f"Tool '{tool_name}' requires human approval before execution.",
            }
        return {"status": "allow"}

    def wait_for_tool_approval(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Offline mode: no approver is available, so pending tools are denied."""
        tool_name = serialized.get("name", "")
        return {
            "status": "deny",
            "reason": (
                f"Tool '{tool_name}' requires approval, but no approver is available "
                "in offline mode."
            ),
        }

    def on_graph_node_start(self, **kwargs: Any) -> None:
        """Record graph node entry (topology hook)."""

    def on_graph_node_end(self, **kwargs: Any) -> None:
        """Record graph node exit (topology hook)."""
