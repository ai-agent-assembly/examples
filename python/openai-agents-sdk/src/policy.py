"""Local offline policy engine for the openai-agents-sdk example.

Simulates Agent Assembly gateway policy enforcement, including an approval
gate for tools that require human sign-off before execution.

Production setup:
    ctx = init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent")
    # Policy rules (including approval gates) are configured in the gateway.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

DENIED_TOOLS: frozenset[str] = frozenset({
    "delete_record",
    "drop_table",
})

APPROVAL_REQUIRED_TOOLS: frozenset[str] = frozenset({
    "send_message_to_user",
    "trigger_payment",
})


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy, including approval gates.

    check_tool_start returns:
      - "allow"   — tool proceeds immediately
      - "deny"    — tool is blocked; raises ToolExecutionBlockedError
      - "pending" — tool needs approval; wait_for_tool_approval is called next
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
                    f"Tool '{tool_name}' is permanently blocked by policy rule "
                    "'deny_destructive_data_ops'."
                ),
            }
        if tool_name in APPROVAL_REQUIRED_TOOLS:
            return {
                "status": "pending",
                "reason": (
                    f"Tool '{tool_name}' requires human approval before execution."
                ),
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
