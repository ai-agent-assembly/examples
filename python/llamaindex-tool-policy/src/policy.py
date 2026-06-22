"""Local offline policy engine for the llamaindex-tool-policy example.

LlamaIndex now has a native Agent Assembly adapter
(``agent_assembly.adapters.llamaindex``). It monkey-patches the concrete
``FunctionTool.call`` / ``acall`` execution methods so every tool invocation
passes through governance automatically — no per-call wrapper is needed.

The adapter calls ``interceptor.check_tool_start(...)`` before a tool body runs
and blocks on a ``deny`` (returning a ``[BLOCKED by governance policy]``
``ToolOutput`` rather than raising, so an agent loop can react). This module
provides ``LocalPolicyEngine`` — the interceptor that simulates gateway policy
offline (allow / deny) — which is what ``main.py`` hands to the adapter.

The ``_enforce = True`` flag puts the interceptor in fail-closed posture: an
unknown / malformed verdict denies rather than silently allowing (AAASM-3107).
"""

from __future__ import annotations

from typing import Any

DENIED_TOOLS: frozenset[str] = frozenset(
    {
        "execute_sql",
        "run_shell_command",
    }
)


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    Implements the ``check_tool_start`` interceptor contract the LlamaIndex
    adapter calls before a governed ``FunctionTool`` runs. Returns an
    ``{"status": "allow"}`` / ``{"status": "deny", "reason": ...}`` verdict.
    """

    #: Fail-closed posture: the adapter denies an unknown verdict under enforce.
    _enforce = True

    def check_tool_start(self, **kwargs: Any) -> dict[str, str]:
        tool_name = str(kwargs.get("tool_name") or "")
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule 'deny_arbitrary_execution'."
                ),
            }
        return {"status": "allow"}
