"""Local offline policy engine for the semantic-kernel-tool-policy example.

Microsoft Semantic Kernel has **no native Agent Assembly adapter** (it is
distinct from the Microsoft Agent Framework, which does), so this example governs
it the framework-agnostic way — the same path the ``custom-tool-policy`` example
uses. Every real ``KernelFunction`` invocation is routed through Agent Assembly's
callback host (``AssemblyCallbackHandler``), which consults this policy's
``check_tool_start`` *before* the function body runs. A ``deny`` short-circuits
the function by raising ``ToolExecutionBlockedError``; the body never executes.

In production, ``init_assembly()`` wires the live runtime as the interceptor and
the gateway answers each allow/deny decision. This ``LocalPolicyEngine``
simulates those verdicts offline, so the demo runs with no gateway or API key.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments, KernelFunction

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


async def governed_invoke(
    kernel: Kernel,
    function: KernelFunction,
    arguments: KernelArguments,
    policy: LocalPolicyEngine,
) -> str:
    """Invoke a real ``KernelFunction`` through an Agent Assembly policy check.

    Consults ``policy`` before invoking the function's execution chokepoint
    (``Kernel.invoke``) — a denied function raises ``ToolExecutionBlockedError``
    and its body never runs. Returns the function result rendered as a string,
    exactly as Semantic Kernel surfaces a function result.
    """
    handler = AssemblyCallbackHandler(interceptor=policy)
    handler.on_tool_start(
        serialized={"name": function.name, "type": "tool"},
        input_str=json.dumps({k: str(v) for k, v in arguments.items()}),
        run_id=uuid4(),
    )
    result = await kernel.invoke(function, arguments)
    return str(result)
