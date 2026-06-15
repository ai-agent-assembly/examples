"""Local offline policy engine for the pydantic-ai-governed-agent example.

In production, Agent Assembly's gateway enforces policy server-side. This
module simulates that governance layer locally so the demo runs without a
running gateway.

The ``PydanticAIAdapter`` installs a version-tolerant tool hook — it patches
``pydantic_ai.toolsets.AbstractToolset.call_tool`` (and concrete toolsets such
as ``FunctionToolset``) on pydantic-ai >=0.3.0, falling back to
``pydantic_ai.tools.Tool._run`` on <0.3.0 — and routes every tool invocation
through ``check_tool_start`` below. A ``deny`` (or an unapproved ``pending``)
decision raises ``PolicyViolationError`` before the tool body runs.

Production setup:
    ctx = init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent")
    # Policy rules are defined in the gateway; the SDK enforces them automatically.
"""
from __future__ import annotations

from typing import Any

DENIED_TOOLS: frozenset[str] = frozenset({
    "delete_records",
    "write_file",
})

PENDING_TOOLS: frozenset[str] = frozenset({
    "send_email",
})


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    The Pydantic AI adapter calls ``check_tool_start`` (and, for pending
    tools, ``wait_for_tool_approval``) as ``async`` hooks. Both return decision
    dicts in the gateway wire format: ``{"status": "allow" | "deny" | "pending"}``.
    """

    async def check_tool_start(self, **kwargs: Any) -> dict[str, str]:
        tool_name = str(kwargs.get("tool_name", ""))
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

    async def wait_for_tool_approval(self, **kwargs: Any) -> dict[str, str]:
        """Offline mode: no approver is available, so pending tools are denied."""
        tool_name = str(kwargs.get("tool_name", ""))
        return {
            "status": "deny",
            "reason": (
                f"Tool '{tool_name}' requires approval, but no approver is available "
                "in offline mode."
            ),
        }
