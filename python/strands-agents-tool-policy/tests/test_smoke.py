"""Smoke tests for strands-agents-tool-policy — offline, no gateway or API key.

These drive real Strands ``@tool`` objects through the Agent Assembly policy
check and assert genuine governance: a denied tool's body is short-circuited
before it runs, an allowed tool runs and returns its real output. The deny test
is the negative control — it fails if governance is a no-op.
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


def test_get_weather_is_allowed(policy: LocalPolicyEngine) -> None:
    result = governed_run(get_weather, {"city": "London"}, policy)
    assert "London" in str(result)


def test_summarize_docs_is_allowed(policy: LocalPolicyEngine) -> None:
    result = governed_run(summarize_docs, {"topic": "governance"}, policy)
    assert "governance" in str(result)


def test_execute_sql_is_denied(policy: LocalPolicyEngine) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="deny_arbitrary_execution"):
        governed_run(execute_sql, {"sql": "SELECT * FROM secrets"}, policy)


def test_denied_tool_body_does_not_run(policy: LocalPolicyEngine) -> None:
    # Negative control: a no-op governance path would let the body run ->
    # SQL_EXECUTIONS would record the statement.
    with pytest.raises(ToolExecutionBlockedError):
        governed_run(execute_sql, {"sql": "DROP TABLE users"}, policy)
    assert SQL_EXECUTIONS == [], "denied tool body executed — governance is a no-op"


def test_allowed_tool_body_runs(policy: LocalPolicyEngine) -> None:
    result = governed_run(get_weather, {"city": "Paris"}, policy)
    assert "Paris" in str(result)


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from unittest.mock import patch

    from agent_assembly import init_assembly
    from agent_assembly.adapters.registry import AdapterRegistry

    # AAASM-6156 -- patch adapter *discovery*, not the private
    # ``_register_adapters`` helper the examples used to reach for. Discovery's
    # contract is "the available adapters, in priority order", which does not
    # move with the SDK's internal return shape; that helper's did (rc.7 made it
    # return a 2-tuple), and because all 16 Python examples pinned the old shape
    # the same upgrade broke every one of them at once.
    #
    # ``_start_network_layer`` needs no patch either: under ``mode="sdk-only"``
    # the real function is already a no-op returning exactly what the old mock
    # returned, so patching it only pinned a second internal shape.
    with patch.object(AdapterRegistry, "get_available_adapters_by_priority", return_value=[]):
        ctx = init_assembly(
            gateway_url="http://localhost:8080",
            agent_id="test-strands-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-strands-agent"
        finally:
            ctx.shutdown()
