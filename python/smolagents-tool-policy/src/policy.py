"""Local offline policy engine for the smolagents-tool-policy example.

In production, Agent Assembly's gateway enforces policy server-side. This module
simulates that governance layer locally so the demo runs without a running
gateway.

The ``SmolagentsAdapter`` patches ``smolagents.tools.Tool.__call__`` — the
chokepoint every tool execution flows through (``Tool.__call__`` runs
``self.forward(...)``) — and routes every tool invocation through
``check_tool_start`` below *before* the tool body runs. A ``deny`` decision makes
the adapter return the ``[BLOCKED by governance policy]`` message instead of
executing ``forward``; an ``allow`` lets the real tool run and records its result.

Production setup:
    ctx = init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent")
    # Policy rules are defined in the gateway; the SDK enforces them automatically
    # the moment smolagents is importable in the process.
"""

from __future__ import annotations

from typing import Any

#: Tools the policy refuses outright. The destructive shell tool models the class
#: of action you never want an autonomous agent to take unsupervised.
DENIED_TOOLS: frozenset[str] = frozenset(
    {
        "run_shell_command",
        "delete_records",
    }
)


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    The smolagents adapter calls ``check_tool_start`` synchronously before a
    governed tool's ``forward`` runs, passing the resolved ``tool_name`` and the
    governed ``args``. It returns a decision dict in the gateway wire format:
    ``{"status": "allow" | "deny", "reason": "..."}``.

    ``_enforce = True`` marks this interceptor as fail-closed (the same flag the
    SDK's real ``RuntimeQueryInterceptor`` carries under ``enforcement_mode =
    "enforce"``), so a malformed or unknown verdict denies rather than silently
    allowing.
    """

    _enforce = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def check_tool_start(self, **kwargs: Any) -> dict[str, str]:
        tool_name = str(kwargs.get("tool_name", ""))
        args = kwargs.get("args") or {}
        self.calls.append((tool_name, dict(args)))
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule 'deny_destructive_operations'."
                ),
            }
        return {"status": "allow"}

    def record_result(self, **kwargs: Any) -> None:
        """Audit sink: the adapter records each allowed tool's result here.

        In production this is where the SDK ships a ``GovernanceEvent`` to the
        gateway over the native transport; offline we simply ignore it.
        """
        del kwargs
