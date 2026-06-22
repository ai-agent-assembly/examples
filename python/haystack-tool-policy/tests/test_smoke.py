"""Smoke tests for haystack-tool-policy — offline, no gateway or API key required.

These prove the native Haystack adapter genuinely governs real ``haystack.tools.Tool``
instances: an allowed tool runs and a denied tool is short-circuited *before its body
executes* (the no-op guard — a pass-through adapter would let the body run and fail
``test_denied_tool_body_never_runs``).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("haystack.tools", reason="haystack-ai is not installed")

from haystack.tools import Tool  # noqa: E402

from agent_assembly.adapters.haystack import HaystackPatch  # noqa: E402

from src import tools as tools_module  # noqa: E402
from src.policy import LocalPolicyEngine  # noqa: E402
from src.tools import build_tools  # noqa: E402

_BLOCKED_MARKER = "[BLOCKED by governance policy]"


@pytest.fixture
def governed() -> Iterator[list[Tool]]:
    tools_module.EXECUTED.clear()
    patch = HaystackPatch(LocalPolicyEngine())
    assert patch.apply() is True, "Haystack adapter did not install"
    try:
        yield build_tools()
    finally:
        patch.revert()
        tools_module.EXECUTED.clear()


def _by_name(tools: list[Tool], name: str) -> Tool:
    return next(t for t in tools if t.name == name)


def test_allowed_tool_runs(governed: list[Tool]) -> None:
    result = _by_name(governed, "query_index").invoke(query="agent assembly docs")
    assert "Index results" in result
    assert _BLOCKED_MARKER not in result
    assert tools_module.EXECUTED == ["query_index"]


def test_summarize_tool_runs(governed: list[Tool]) -> None:
    result = _by_name(governed, "summarize_docs").invoke(topic="governance")
    assert "Summary for" in result
    assert _BLOCKED_MARKER not in result


def test_denied_tool_is_blocked(governed: list[Tool]) -> None:
    result = _by_name(governed, "execute_sql").invoke(sql="DROP TABLE users; --")
    assert _BLOCKED_MARKER in result
    assert "deny_arbitrary_execution" in result


def test_denied_tool_body_never_runs(governed: list[Tool]) -> None:
    """The no-op guard: a denied tool's underlying function must not execute."""
    _by_name(governed, "execute_sql").invoke(sql="SELECT * FROM secrets")
    assert "execute_sql" not in tools_module.EXECUTED, (
        "deny let the tool body run — governance is a no-op!"
    )


def test_denied_tool_runs_normally_after_revert() -> None:
    """After revert the same tool runs — proving the adapter was the only gate."""
    tools_module.EXECUTED.clear()
    patch = HaystackPatch(LocalPolicyEngine())
    assert patch.apply() is True
    sql_tool = _by_name(build_tools(), "execute_sql")
    blocked = sql_tool.invoke(sql="DROP TABLE users")
    assert _BLOCKED_MARKER in blocked
    patch.revert()

    sql_tool_after = _by_name(build_tools(), "execute_sql")
    out = sql_tool_after.invoke(sql="DROP TABLE users")
    assert _BLOCKED_MARKER not in out
    assert "execute_sql" in tools_module.EXECUTED
    tools_module.EXECUTED.clear()


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from unittest.mock import patch as mock_patch

    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with (
        mock_patch.object(_core, "_register_adapters", return_value=[]),
        mock_patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ),
    ):
        ctx = init_assembly(
            gateway_url="http://localhost:8080",
            agent_id="test-haystack-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-haystack-agent"
        finally:
            ctx.shutdown()
