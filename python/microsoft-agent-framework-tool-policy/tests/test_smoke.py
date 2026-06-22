"""Smoke tests for microsoft-agent-framework-governed-agent — offline, no gateway.

These prove the example *genuinely governs* the real framework: with the adapter
installed, a denied tool's `FunctionTool.invoke` raises before its body runs,
while an allowed tool's body executes (a negative control against a no-op).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip(
    "agent_framework",
    reason="agent-framework not installed — `uv sync --extra dev` (with "
    "--prerelease=allow) installs it to run these smokes",
)

from agent_assembly.adapters.microsoft_agent_framework import (  # noqa: E402
    MicrosoftAgentFrameworkAdapter,
)
from agent_assembly.exceptions import PolicyViolationError  # noqa: E402

from src.policy import LocalPolicyEngine  # noqa: E402
from src.tools import build_tools, tool_arguments  # noqa: E402


@pytest.fixture
def governed_adapter() -> MicrosoftAgentFrameworkAdapter:
    adapter = MicrosoftAgentFrameworkAdapter()
    adapter.set_process_agent_id("test-maf-agent")
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


async def test_allowed_tool_runs_through_invoke(
    governed_adapter: MicrosoftAgentFrameworkAdapter,
) -> None:
    tool = build_tools()["get_weather"]
    result = await tool.invoke(arguments=tool_arguments("get_weather"))
    assert result is not None


async def test_denied_tool_raises_policy_violation(
    governed_adapter: MicrosoftAgentFrameworkAdapter,
) -> None:
    tool = build_tools()["delete_records"]
    with pytest.raises(PolicyViolationError, match="blocked by governance policy"):
        await tool.invoke(arguments=tool_arguments("delete_records"))


async def test_pending_tool_raises_policy_violation(
    governed_adapter: MicrosoftAgentFrameworkAdapter,
) -> None:
    tool = build_tools()["send_email"]
    with pytest.raises(PolicyViolationError, match="rejected during approval"):
        await tool.invoke(arguments=tool_arguments("send_email"))


async def test_denied_tool_body_does_not_run(
    governed_adapter: MicrosoftAgentFrameworkAdapter,
) -> None:
    """Negative control: a denied tool must be short-circuited, not merely raise.

    Build a tool whose body records a side effect, deny it, and assert the side
    effect never happens — proving the hook governs rather than no-ops.
    """
    import agent_framework as af

    ran: list[str] = []

    # `agent_framework` ships no type stubs, so `af.tool` is an untyped (`Any`)
    # decorator; the scoped ignore is the genuine framework limitation, not a
    # real typing defect (mirrors src/tools.py).
    @af.tool  # type: ignore[untyped-decorator]
    def delete_records(path: str) -> str:
        """Delete records (denied by policy)."""
        ran.append(path)
        return f"deleted {path}"

    with pytest.raises(PolicyViolationError):
        await delete_records.invoke(arguments={"path": "/x"})
    assert ran == []


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-maf-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-maf-agent"
                assert ctx.network_mode == "sdk-only"
            finally:
                ctx.shutdown()
