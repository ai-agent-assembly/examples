"""Smoke tests for semantic-kernel-tool-policy — offline, no gateway or API key.

These drive real Semantic Kernel ``KernelFunction`` objects through the Agent
Assembly policy check and assert genuine governance: a denied function's body is
short-circuited before it runs, an allowed function runs and returns its real
output. The deny test is the negative control — it fails if governance is a
no-op.
"""

from __future__ import annotations

import pytest
from semantic_kernel.functions import KernelArguments

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed_invoke
from src.tools import PLUGIN_NAME, SQL_EXECUTIONS, build_kernel


@pytest.fixture
def policy() -> LocalPolicyEngine:
    SQL_EXECUTIONS.clear()
    return LocalPolicyEngine()


async def test_get_weather_is_allowed(policy: LocalPolicyEngine) -> None:
    kernel = build_kernel()
    fn = kernel.get_function(PLUGIN_NAME, "get_weather")
    result = await governed_invoke(kernel, fn, KernelArguments(city="London"), policy)
    assert "London" in result


async def test_summarize_docs_is_allowed(policy: LocalPolicyEngine) -> None:
    kernel = build_kernel()
    fn = kernel.get_function(PLUGIN_NAME, "summarize_docs")
    result = await governed_invoke(
        kernel, fn, KernelArguments(topic="governance"), policy
    )
    assert "governance" in result


async def test_execute_sql_is_denied(policy: LocalPolicyEngine) -> None:
    kernel = build_kernel()
    fn = kernel.get_function(PLUGIN_NAME, "execute_sql")
    args = KernelArguments(sql="SELECT * FROM secrets")
    with pytest.raises(ToolExecutionBlockedError, match="deny_arbitrary_execution"):
        await governed_invoke(kernel, fn, args, policy)


async def test_denied_tool_body_does_not_run(policy: LocalPolicyEngine) -> None:
    # Negative control: a no-op governance path would let the body run ->
    # SQL_EXECUTIONS would record the statement.
    kernel = build_kernel()
    fn = kernel.get_function(PLUGIN_NAME, "execute_sql")
    args = KernelArguments(sql="DROP TABLE users")
    with pytest.raises(ToolExecutionBlockedError):
        await governed_invoke(kernel, fn, args, policy)
    assert SQL_EXECUTIONS == [], "denied tool body executed — governance is a no-op"


async def test_allowed_tool_body_runs(policy: LocalPolicyEngine) -> None:
    kernel = build_kernel()
    fn = kernel.get_function(PLUGIN_NAME, "get_weather")
    result = await governed_invoke(kernel, fn, KernelArguments(city="Paris"), policy)
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
            agent_id="test-semantic-kernel-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-semantic-kernel-agent"
        finally:
            ctx.shutdown()
