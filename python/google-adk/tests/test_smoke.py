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
    with pytest.raises(PolicyViolationError, match="blocked by governance policy"):
        await tool.run_async(args={}, tool_context=_tool_context())


async def test_pending_tool_raises_policy_violation(governed_tool_class: type[DemoTool]) -> None:
    tool = build_tools()["send_email"]
    with pytest.raises(PolicyViolationError, match="rejected during approval"):
        await tool.run_async(args={}, tool_context=_tool_context())


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
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
