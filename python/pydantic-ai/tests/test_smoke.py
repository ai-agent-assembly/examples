"""Smoke tests for pydantic-ai-governed-agent — offline, no gateway required."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_assembly.adapters.pydantic_ai import PydanticAIAdapter
from agent_assembly.exceptions import PolicyViolationError

from src.agent import build_agent
from src.policy import LocalPolicyEngine


@pytest.fixture
def governed_adapter() -> PydanticAIAdapter:
    adapter = PydanticAIAdapter()
    adapter.set_process_agent_id("test-pydantic-ai-agent")
    adapter.register_hooks(LocalPolicyEngine())
    yield adapter
    adapter.unregister_hooks()


async def test_check_tool_start_allows_safe_tool() -> None:
    decision = await LocalPolicyEngine().check_tool_start(tool_name="get_weather")
    assert decision["status"] == "allow"


async def test_check_tool_start_denies_destructive_tool() -> None:
    decision = await LocalPolicyEngine().check_tool_start(tool_name="delete_records")
    assert decision["status"] == "deny"
    assert "deny_destructive_operations" in decision["reason"]


async def test_pending_tool_denied_without_approver() -> None:
    decision = await LocalPolicyEngine().wait_for_tool_approval(tool_name="send_email")
    assert decision["status"] == "deny"
    assert "no approver is available" in decision["reason"]


async def test_allowed_tool_runs_through_agent(governed_adapter: PydanticAIAdapter) -> None:
    agent = build_agent("get_weather")
    result = await agent.run("please run the task")
    assert result is not None


async def test_denied_tool_raises_policy_violation(governed_adapter: PydanticAIAdapter) -> None:
    agent = build_agent("delete_records")
    with pytest.raises(PolicyViolationError, match="blocked by governance policy"):
        await agent.run("please run the task")


async def test_pending_tool_raises_policy_violation(governed_adapter: PydanticAIAdapter) -> None:
    agent = build_agent("send_email")
    with pytest.raises(PolicyViolationError, match="rejected during approval"):
        await agent.run("please run the task")


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
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
            agent_id="test-pydantic-ai-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-pydantic-ai-agent"
            assert ctx.network_mode == "sdk-only"
        finally:
            ctx.shutdown()
