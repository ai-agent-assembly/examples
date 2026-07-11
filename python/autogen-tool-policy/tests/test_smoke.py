"""Smoke tests for autogen-tool-policy — offline, no gateway or API key required.

These drive real AutoGen ``FunctionTool`` objects through the Agent Assembly
policy check and assert genuine governance: a denied tool's body is
short-circuited before it runs, an allowed tool runs and returns its real
output. The deny test is the negative control — it fails if governance is a
no-op.
"""

from __future__ import annotations

import pytest

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed_run
from src.tools import SQL_EXECUTIONS, execute_sql, get_weather, summarize_docs


@pytest.fixture
def policy() -> LocalPolicyEngine:
    SQL_EXECUTIONS.clear()
    return LocalPolicyEngine()


async def test_get_weather_is_allowed(policy: LocalPolicyEngine) -> None:
    result = await governed_run(get_weather, {"city": "London"}, policy)
    assert "London" in result


async def test_summarize_docs_is_allowed(policy: LocalPolicyEngine) -> None:
    result = await governed_run(summarize_docs, {"topic": "governance"}, policy)
    assert "governance" in result


async def test_execute_sql_is_denied(policy: LocalPolicyEngine) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="deny_arbitrary_execution"):
        await governed_run(execute_sql, {"sql": "SELECT * FROM secrets"}, policy)


async def test_denied_tool_body_does_not_run(policy: LocalPolicyEngine) -> None:
    # Negative control: a no-op governance path would let the body run ->
    # SQL_EXECUTIONS would record the statement.
    with pytest.raises(ToolExecutionBlockedError):
        await governed_run(execute_sql, {"sql": "DROP TABLE users"}, policy)
    assert SQL_EXECUTIONS == [], "denied tool body executed — governance is a no-op"


async def test_allowed_tool_body_runs(policy: LocalPolicyEngine) -> None:
    result = await governed_run(get_weather, {"city": "Paris"}, policy)
    assert "Paris" in result


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
            agent_id="test-autogen-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-autogen-agent"
        finally:
            ctx.shutdown()
