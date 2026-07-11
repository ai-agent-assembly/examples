"""Local offline policy engine for the strands-agents-tool-policy example.

Strands Agents (AWS) has **no native Agent Assembly adapter**, so this example
governs it the framework-agnostic way — the same path the ``custom-tool-policy``
example uses. Every real ``@strands.tool`` invocation is routed through Agent
Assembly's callback host (``AssemblyCallbackHandler``), which consults this
policy's ``check_tool_start`` *before* the tool body runs. A ``deny``
short-circuits the tool by raising ``ToolExecutionBlockedError``; the body never
executes.

In production, ``init_assembly()`` wires the live runtime as the interceptor and
the gateway answers each allow/deny decision. This ``LocalPolicyEngine``
simulates those verdicts offline, so the demo runs with no gateway or API key.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from strands.tools.decorator import DecoratedFunctionTool

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

#: Tools denied by this demo policy — destructive or arbitrary-execution actions.
DENIED_TOOLS: frozenset[str] = frozenset(
    {
        "execute_sql",
        "run_shell_command",
    }
)


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode.

    Implements the interceptor contract the callback host calls before running a
    tool: ``check_tool_start`` returns ``{"status": "allow"}`` or
    ``{"status": "deny", "reason": ...}``. ``_enforce = True`` puts the engine in
    the fail-closed posture so an unknown verdict denies rather than allows.
    """

    _enforce = True

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, str]:
        del kwargs
        tool_name = serialized.get("name", "")
        if tool_name in DENIED_TOOLS:
            return {
                "status": "deny",
                "reason": (
                    f"Tool '{tool_name}' is blocked by policy rule 'deny_arbitrary_execution'."
                ),
            }
        return {"status": "allow"}


def governed_run(
    tool: DecoratedFunctionTool,
    arguments: Mapping[str, Any],
    policy: LocalPolicyEngine,
) -> str:
    """Run a real Strands ``@tool`` through an Agent Assembly policy check.

    Consults ``policy`` before invoking the tool — a denied tool raises
    ``ToolExecutionBlockedError`` and its body never runs. Returns the tool's
    result, exactly as a Strands ``Agent`` surfaces a tool result.
    """
    handler = AssemblyCallbackHandler(interceptor=policy)
    handler.on_tool_start(
        serialized={"name": tool.tool_name, "type": "tool"},
        input_str=json.dumps(dict(arguments)),
        run_id=uuid4(),
    )
    return tool(**arguments)
