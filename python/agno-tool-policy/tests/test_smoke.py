"""Smoke tests for agno-tool-policy — offline, no gateway or API key required.

These drive real Agno ``@tool`` functions through the SDK's real ``AgnoPatch``
(the native Agno adapter) and assert genuine governance: a denied tool's body is
short-circuited before it runs, an allowed tool runs and returns its real output.
The deny test is the negative control — it fails if governance is a no-op.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from agno.tools.function import Function, FunctionCall, FunctionExecutionResult

from agent_assembly.adapters.agno import AgnoPatch

from src.policy import LocalPolicyEngine
from src.tools import SQL_EXECUTIONS, execute_sql, get_weather, summarize_docs

_BLOCKED_MARKER = "[BLOCKED by governance policy]"


@pytest.fixture
def governed() -> Iterator[None]:
    """Apply the real Agno governance hook for the test, then revert it."""
    SQL_EXECUTIONS.clear()
    patch = AgnoPatch(LocalPolicyEngine())
    assert patch.apply() is True, "Agno governance hook did not install"
    try:
        yield
    finally:
        patch.revert()


def _run(function: Function, arguments: dict[str, Any]) -> FunctionExecutionResult:
    return FunctionCall(function=function, arguments=arguments).execute()


def test_get_weather_is_allowed(governed: None) -> None:
    result = _run(get_weather, {"city": "London"})
    assert result.status == "success"
    assert "London" in str(result.result)


def test_summarize_docs_is_allowed(governed: None) -> None:
    result = _run(summarize_docs, {"topic": "governance"})
    assert result.status == "success"
    assert "governance" in str(result.result)


def test_execute_sql_is_denied(governed: None) -> None:
    result = _run(execute_sql, {"sql": "SELECT * FROM secrets"})
    assert result.status == "failure"
    assert _BLOCKED_MARKER in str(result.error)
    assert "deny_arbitrary_execution" in str(result.error)


def test_denied_tool_body_does_not_run(governed: None) -> None:
    # Negative control: a no-op patch would let the body run -> SQL_EXECUTIONS
    # would record the statement.
    _run(execute_sql, {"sql": "DROP TABLE users"})
    assert SQL_EXECUTIONS == [], "denied tool body executed — governance is a no-op"


def test_allowed_tool_body_runs() -> None:
    # Without the patch applied, the real tool body runs and returns its output.
    result = _run(get_weather, {"city": "Paris"})
    assert result.status == "success"
    assert "Paris" in str(result.result)


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from unittest.mock import patch

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
            agent_id="test-agno-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-agno-agent"
        finally:
            ctx.shutdown()
