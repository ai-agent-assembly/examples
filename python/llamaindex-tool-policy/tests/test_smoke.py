"""Smoke tests for llamaindex-tool-policy — offline, no gateway or API key required.

These drive the **real** LlamaIndex adapter: ``LlamaIndexAdapter.register_hooks``
patches ``FunctionTool.call``, so an allowed tool runs and a denied tool's body
never executes (the adapter returns a ``[BLOCKED by governance policy]``
``ToolOutput`` instead of raising). Each test reverts the patch so the global
``FunctionTool`` class is left clean.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from llama_index.core.tools import FunctionTool

from agent_assembly.adapters.llamaindex import LlamaIndexAdapter

from src.policy import LocalPolicyEngine

_BLOCKED_MARKER = "[BLOCKED by governance policy]"


@pytest.fixture
def governed() -> Iterator[None]:
    """Register the LlamaIndex adapter against the local policy; revert after."""
    adapter = LlamaIndexAdapter()
    adapter.register_hooks(LocalPolicyEngine())
    try:
        yield
    finally:
        adapter.unregister_hooks()


def _make_tool(name: str, calls: list[str]) -> FunctionTool:
    def fn(value: str = "") -> str:
        calls.append(value)
        return f"ran {name}({value})"

    return FunctionTool.from_defaults(fn=fn, name=name)


def test_query_index_is_allowed(governed: None) -> None:
    calls: list[str] = []
    tool = _make_tool("query_index", calls)
    output = tool.call(value="agent assembly docs")
    assert calls == ["agent assembly docs"]
    assert _BLOCKED_MARKER not in str(output.content)


def test_execute_sql_is_denied(governed: None) -> None:
    calls: list[str] = []
    tool = _make_tool("execute_sql", calls)
    output = tool.call(value="SELECT * FROM secrets")
    assert calls == [], "denied tool body must not execute"
    assert _BLOCKED_MARKER in str(output.content)
    assert "deny_arbitrary_execution" in str(output.content)


def test_run_shell_command_is_denied(governed: None) -> None:
    calls: list[str] = []
    tool = _make_tool("run_shell_command", calls)
    output = tool.call(value="rm -rf /")
    assert calls == []
    assert _BLOCKED_MARKER in str(output.content)


def test_unknown_tool_is_allowed(governed: None) -> None:
    calls: list[str] = []
    tool = _make_tool("list_indexes", calls)
    output = tool.call(value="x")
    assert calls == ["x"]
    assert _BLOCKED_MARKER not in str(output.content)


def test_revert_restores_ungoverned_behavior() -> None:
    """After unregister, a previously-denied tool name runs normally again."""
    calls: list[str] = []
    adapter = LlamaIndexAdapter()
    adapter.register_hooks(LocalPolicyEngine())
    adapter.unregister_hooks()

    tool = _make_tool("execute_sql", calls)
    output = tool.call(value="SELECT 1")
    assert calls == ["SELECT 1"], "tool must run once governance hooks are reverted"
    assert _BLOCKED_MARKER not in str(output.content)


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from unittest.mock import patch

    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-llamaindex-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-llamaindex-agent"
            finally:
                ctx.shutdown()
