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


def test_init_assembly_sdk_only_requires_no_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    from agent_assembly import init_assembly
    from agent_assembly.adapters.registry import AdapterRegistry

    # AAASM-6196 -- make "no gateway" a fact instead of an assumption about the
    # machine. Nothing here used to stop a locally running gateway from answering:
    # ``gateway_url`` steers only the *host*, because the resolver always
    # substitutes the fixed gRPC port 50051. ``AA_GATEWAY_ENDPOINT`` is the one
    # lever honoured verbatim. Port 1 is privileged, so no user process can
    # occupy it and the connection is refused immediately.
    monkeypatch.setenv("AA_GATEWAY_ENDPOINT", "http://127.0.0.1:1")

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
            agent_id="test-semantic-kernel-agent",
            mode="sdk-only",
            # AAASM-6204: the default posture fails closed when registration
            # can't reach a gateway, and this test asserts the offline path.
            enforcement_mode="observe",
        )
        try:
            assert ctx.client.agent_id == "test-semantic-kernel-agent"
        finally:
            ctx.shutdown()
