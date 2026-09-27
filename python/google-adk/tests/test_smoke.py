"""Smoke tests for google-adk-governed-agent — offline, no gateway required."""
from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent_assembly.exceptions import PolicyViolationError

from src.governance import govern_tool_class, ungovern_tool_class
from src.policy import LocalPolicyEngine
from src.tools import DemoTool, build_tools


def _tool_context() -> SimpleNamespace:
    return SimpleNamespace(
        invocation_context=SimpleNamespace(
            assembly_agent_id="test-google-adk-agent",
            invocation_id="test-run",
        ),
    )


@pytest.fixture
def governed_tool_class() -> Iterator[type[DemoTool]]:
    govern_tool_class(DemoTool, LocalPolicyEngine())
    yield DemoTool
    ungovern_tool_class(DemoTool)


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


async def test_allowed_tool_runs(governed_tool_class: type[DemoTool]) -> None:
    tool = build_tools()["get_weather"]
    result = await tool.run_async(args={}, tool_context=_tool_context())
    assert "mock response" in result


async def test_denied_tool_raises_policy_violation(governed_tool_class: type[DemoTool]) -> None:
    tool = build_tools()["delete_records"]
    ctx = _tool_context()
    with pytest.raises(PolicyViolationError, match="blocked by governance policy"):
        await tool.run_async(args={}, tool_context=ctx)


async def test_pending_tool_raises_policy_violation(governed_tool_class: type[DemoTool]) -> None:
    tool = build_tools()["send_email"]
    ctx = _tool_context()
    with pytest.raises(PolicyViolationError, match="rejected during approval"):
        await tool.run_async(args={}, tool_context=ctx)


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
            agent_id="test-google-adk-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-google-adk-agent"
            assert ctx.network_mode == "sdk-only"
        finally:
            ctx.shutdown()
