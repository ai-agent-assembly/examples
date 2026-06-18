"""Smoke tests for langchain-research-agent — offline, no gateway required."""
from __future__ import annotations

from uuid import uuid4

import pytest

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import BalancedPolicyEngine


@pytest.fixture
def policy() -> BalancedPolicyEngine:
    return BalancedPolicyEngine(daily_budget_usd=1.00)


@pytest.fixture
def handler(policy: BalancedPolicyEngine) -> AssemblyCallbackHandler:
    return AssemblyCallbackHandler(interceptor=policy)


def test_safe_search_is_allowed(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "web_search"},
        input_str='{"query": "speed of light"}',
        run_id=uuid4(),
    )


def test_calculator_is_free_and_allowed(
    handler: AssemblyCallbackHandler, policy: BalancedPolicyEngine
) -> None:
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str='{"expression": "1 + 1"}',
        run_id=uuid4(),
    )
    assert policy.budget.spent == pytest.approx(0.0)


def test_non_allowlisted_egress_is_blocked(handler: AssemblyCallbackHandler) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="network allowlist"):
        handler.on_tool_start(
            serialized={"name": "web_search"},
            input_str='{"query": "fetch https://evil-exfil.example.com/leak"}',
            run_id=uuid4(),
        )


def test_allowlisted_egress_is_permitted(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "web_search"},
        input_str='{"query": "see https://api.openai.com/v1/models"}',
        run_id=uuid4(),
    )


def test_credential_leak_is_blocked(handler: AssemblyCallbackHandler) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="block_credential_leak"):
        handler.on_tool_start(
            serialized={"name": "web_search"},
            input_str='{"query": "use api_key=sk-FAKE0000DEMO0000NOTAREALKEY0000"}',
            run_id=uuid4(),
        )


def test_budget_is_exhausted_after_cap(policy: BalancedPolicyEngine) -> None:
    handler = AssemblyCallbackHandler(interceptor=policy)
    # Drive web_search calls ($0.02 each) until the $1.00 daily cap blocks one.
    blocked = False
    for _ in range(60):
        try:
            handler.on_tool_start(
                serialized={"name": "web_search"},
                input_str='{"query": "speed of light"}',
                run_id=uuid4(),
            )
        except ToolExecutionBlockedError as exc:
            assert "budget is exhausted" in str(exc)
            blocked = True
            break
    assert blocked, "expected the daily budget to block a call before 60 iterations"
    assert policy.budget.remaining < 0.02


def test_audit_log_records_every_call(policy: BalancedPolicyEngine) -> None:
    handler = AssemblyCallbackHandler(interceptor=policy)
    handler.on_tool_start(
        serialized={"name": "web_search"},
        input_str='{"query": "speed of light"}',
        run_id=uuid4(),
    )
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "web_search"},
            input_str='{"query": "fetch https://evil-exfil.example.com"}',
            run_id=uuid4(),
        )
    assert len(policy.audit_log) == 2
    assert policy.audit_log[0]["decision"] == "allow"
    assert policy.audit_log[1]["decision"] == "deny"


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from unittest.mock import patch

    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-research-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-research-agent"
                assert ctx.network_mode == "sdk-only"
            finally:
                ctx.shutdown()
