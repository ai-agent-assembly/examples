"""Smoke tests for smolagents-tool-policy — offline, no gateway required.

These exercise the *real* smolagents adapter governing *real* ``smolagents.Tool``
instances: a denied tool's ``forward`` body must not run, an allowed tool's must.
The negative control proves the governance is real, not a no-op.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest

from agent_assembly.adapters.smolagents import SmolagentsAdapter

from src.policy import DENIED_TOOLS, LocalPolicyEngine
from src.tools import build_tools

_BLOCKED_MARKER = "[BLOCKED by governance policy]"


@pytest.fixture
def governed() -> Iterator[LocalPolicyEngine]:
    policy = LocalPolicyEngine()
    adapter = SmolagentsAdapter()
    adapter.register(policy)
    try:
        yield policy
    finally:
        adapter.unregister_hooks()


def test_check_tool_start_allows_safe_tool() -> None:
    decision = LocalPolicyEngine().check_tool_start(tool_name="search_docs", args={})
    assert decision["status"] == "allow"


def test_check_tool_start_denies_destructive_tool() -> None:
    decision = LocalPolicyEngine().check_tool_start(
        tool_name="run_shell_command", args={}
    )
    assert decision["status"] == "deny"
    assert "deny_destructive_operations" in decision["reason"]


def test_allowed_tool_runs(governed: LocalPolicyEngine) -> None:
    result = build_tools()["search_docs"](query="agent assembly docs")
    assert "docs results for" in result
    assert _BLOCKED_MARKER not in result


def test_denied_tool_is_blocked(governed: LocalPolicyEngine) -> None:
    result = build_tools()["run_shell_command"](command="rm -rf /")
    assert isinstance(result, str)
    assert _BLOCKED_MARKER in result
    # forward() returns the executed-command string on success; the block marker
    # proves the real tool body never ran.
    assert "executed shell command" not in result


def test_denied_tool_records_no_execution(governed: LocalPolicyEngine) -> None:
    """The governed call is observed by policy but the body is short-circuited."""
    build_tools()["run_shell_command"](command="DROP TABLE users")
    denied_call = next(c for c in governed.calls if c[0] == "run_shell_command")
    assert denied_call[1] == {"command": "DROP TABLE users"}


def test_negative_control_ungoverned_tool_runs_destructively() -> None:
    """Without the adapter applied, the deny policy cannot block the body — proving
    the governed cases above are real interception, not a no-op."""
    # No adapter registered: the raw tool executes its real forward() body.
    result = build_tools()["run_shell_command"](command="rm -rf /")
    assert "executed shell command" in result
    assert _BLOCKED_MARKER not in result


def test_denied_tools_constant_is_nonempty() -> None:
    assert "run_shell_command" in DENIED_TOOLS


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with (
        patch.object(_core, "_register_adapters", return_value=[]),
        patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ),
    ):
        ctx = init_assembly(
            gateway_url="http://localhost:8080",
            agent_id="test-smolagents-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-smolagents-agent"
        finally:
            ctx.shutdown()
