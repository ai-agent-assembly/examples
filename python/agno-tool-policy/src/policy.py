"""Local offline policy engine for the agno-tool-policy example.

Unlike a framework with no adapter, **Agno has a native Agent Assembly adapter**
(``agent_assembly.adapters.agno``). The SDK governs Agno by monkey-patching
``agno.tools.function.FunctionCall.execute`` — the single chokepoint every Agno
function-tool call runs through — so a governed tool consults this policy's
``check_tool_start`` *before* its body executes. A ``deny`` short-circuits the
tool entirely; the body never runs.

This ``LocalPolicyEngine`` simulates the gateway's allow/deny verdicts offline,
so the demo runs with no gateway or API key. In production the same
``check_tool_start`` contract is answered by the live runtime instead.
"""

from __future__ import annotations

from typing import Any

#: Tools denied by this demo policy — destructive or arbitrary-execution actions.
DENIED_TOOLS: frozenset[str] = frozenset(
    {
        "execute_sql",
        "run_shell_command",
    }
)


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    Implements the interceptor contract the Agno adapter calls before running a
    tool: ``check_tool_start`` returns ``{"status": "allow"}`` or
    ``{"status": "deny", "reason": ...}``. ``_enforce = True`` puts the engine in
    the fail-closed posture so an unknown verdict denies rather than allows.
    """

    _enforce = True

    def check_tool_start(
        self,
        *,
        tool_name: str = "",
        **kwargs: Any,
    ) -> dict[str, str]:
        del kwargs
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule 'deny_arbitrary_execution'."
                ),
            }
        return {"status": "allow"}
