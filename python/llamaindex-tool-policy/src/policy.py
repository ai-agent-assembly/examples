"""Local offline policy engine for the llamaindex-tool-policy example.

LlamaIndex does not yet have a native Agent Assembly adapter, so governance
is applied by explicitly calling GovernedToolRunner.run() before each
LlamaIndex FunctionTool invocation.

This module defines:
  - LocalPolicyEngine — simulates gateway policy (allow / deny)
  - GovernedToolRunner — wraps any callable with AssemblyCallbackHandler
    so every tool invocation passes through governance before execution
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

DENIED_TOOLS: frozenset[str] = frozenset({
    "execute_sql",
    "run_shell_command",
})


class LocalPolicyEngine:
    """Simulates Agent Assembly gateway policy enforcement in offline mode."""

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
                    "'deny_arbitrary_execution'."
                ),
            }
        return {"status": "allow"}


class GovernedToolRunner:
    """Wraps a callable with Agent Assembly governance.

    Use this as a bridge when a framework does not have a native adapter.
    Call ``run()`` instead of invoking the tool directly; governance runs first.

    Example::

        runner = GovernedToolRunner("query_index", query_index_fn, policy)
        result = runner.run(query="What is Agent Assembly?")
    """

    def __init__(
        self,
        tool_name: str,
        fn: Any,
        policy: LocalPolicyEngine,
    ) -> None:
        self._tool_name = tool_name
        self._fn = fn
        self._handler = AssemblyCallbackHandler(interceptor=policy)

    def run(self, **kwargs: Any) -> Any:
        import json

        input_str = json.dumps(kwargs)
        self._handler.on_tool_start(
            serialized={"name": self._tool_name, "type": "tool"},
            input_str=input_str,
            run_id=uuid4(),
        )
        return self._fn(**kwargs)
