"""Local offline policy engine for the haystack-tool-policy example.

Unlike a framework that needs a hand-written tool wrapper, Haystack has a
**native Agent Assembly adapter**: ``HaystackPatch`` monkey-patches
``haystack.tools.Tool.invoke`` so every governed tool consults the policy before
its body runs. This module provides the policy *interceptor* the adapter calls —
the same ``check_tool_start`` contract the SDK hands its adapters in production —
so the example governs real Haystack tools end-to-end without a live gateway.

  - ``LocalPolicyEngine`` — simulates gateway policy (allow / deny) and carries
    the ``_enforce`` flag so the adapter is in fail-closed ``enforce`` posture.
"""

from __future__ import annotations

from typing import Any

#: Tool names this demo policy denies (arbitrary-execution surface).
DENIED_TOOLS: frozenset[str] = frozenset({"execute_sql", "run_shell_command"})


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    Implements the ``check_tool_start`` interceptor contract the Haystack adapter
    invokes before a tool runs. ``_enforce = True`` puts the adapter in the
    fail-closed ``enforce`` posture so a deny actually blocks the tool (and an
    unknown verdict would deny rather than silently allow).
    """

    #: Fail-closed posture marker the adapter reads (AAASM-3106 / AAASM-3107).
    _enforce = True

    def check_tool_start(
        self, *, tool_name: str = "", **_kwargs: Any
    ) -> dict[str, str]:
        """Return an allow/deny verdict for *tool_name*.

        The adapter passes the tool name as a keyword; deny the
        arbitrary-execution tools, allow everything else.
        """
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule 'deny_arbitrary_execution'."
                ),
            }
        return {"status": "allow"}
