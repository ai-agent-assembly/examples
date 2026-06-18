"""Minimal local policy engine for the custom-tool-policy example.

This example has no framework dependency — only ``agent-assembly``.
The policy engine simulates governance with a simple allow/deny rule set.

In production:
    with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
        # ctx.client is the gateway-backed interceptor; use it in place of
        # LocalPolicyEngine below.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

DENIED_TOOLS: frozenset[str] = frozenset({
    "send_http_request",
    "write_to_disk",
})


class LocalPolicyEngine:
    """Minimal policy engine: deny specific tool names, allow everything else."""

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule "
                    "'deny_network_and_disk_writes'."
                ),
            }
        return {"status": "allow"}


def governed(tool_name: str, fn: Any, policy: LocalPolicyEngine) -> Any:
    """Wrap a plain Python function with governance.

    Returns a new callable that runs the policy check before calling ``fn``.
    Raises ``ToolExecutionBlockedError`` if the policy denies the tool.
    """
    handler = AssemblyCallbackHandler(interceptor=policy)

    def _wrapper(**kwargs: Any) -> Any:
        import json

        handler.on_tool_start(
            serialized={"name": tool_name, "type": "tool"},
            input_str=json.dumps(kwargs),
            run_id=uuid4(),
        )
        return fn(**kwargs)

    _wrapper.__name__ = tool_name
    return _wrapper
