"""Smoke tests for the approval-gates scenario — offline, no gateway."""
from __future__ import annotations

import pytest

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.approval import ApprovalPolicyEngine, MockApprovalClient, governed, load_policy
from src.tools import get_balance, transfer_funds


@pytest.fixture
def mock_client() -> MockApprovalClient:
    return MockApprovalClient(auto_approve=True)


@pytest.fixture
def rejecting_client() -> MockApprovalClient:
    return MockApprovalClient(auto_approve=False)


@pytest.fixture
def policy(mock_client: MockApprovalClient) -> ApprovalPolicyEngine:
    return ApprovalPolicyEngine(mock_client)


def test_policy_yaml_loads() -> None:
    data = load_policy()
    assert "rules" in data
    rules_by_tool = {r["tool"]: r for r in data["rules"]}
    assert "transfer_funds" in rules_by_tool
    assert rules_by_tool["transfer_funds"]["action"] == "approval_required"
    assert "get_balance" in rules_by_tool
    assert rules_by_tool["get_balance"]["action"] == "allow"


def test_get_balance_is_allowed(policy: ApprovalPolicyEngine) -> None:
    fn = governed("get_balance", get_balance, policy)
    result = fn(account_id="acc-001")
    assert "$" in result


def test_transfer_funds_executes_after_approval(policy: ApprovalPolicyEngine) -> None:
    fn = governed("transfer_funds", transfer_funds, policy)
    result = fn(from_account="acc-001", to_account="acc-002", amount=100.0)
    assert "Transferred" in result
    assert "acc-001" in result
    assert "acc-002" in result


def test_transfer_funds_blocked_when_rejected(rejecting_client: MockApprovalClient) -> None:
    policy = ApprovalPolicyEngine(rejecting_client)
    fn = governed("transfer_funds", transfer_funds, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(from_account="acc-001", to_account="acc-002", amount=100.0)


def test_transfer_body_does_not_execute_when_rejected(rejecting_client: MockApprovalClient) -> None:
    called: list[str] = []
    policy = ApprovalPolicyEngine(rejecting_client)
    fn = governed("transfer_funds", lambda **kw: called.append(str(kw)), policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(from_account="acc-001", to_account="acc-002", amount=50.0)
    assert called == [], "rejected tool body must not execute"


def test_unknown_tool_uses_default_deny(policy: ApprovalPolicyEngine) -> None:
    fn = governed("execute_shell", lambda cmd: cmd, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(cmd="rm -rf /")


def test_mock_approval_client_auto_approves(mock_client: MockApprovalClient) -> None:
    request_id = mock_client.request_approval("transfer_funds", "{}")
    assert mock_client.wait_for_approval(request_id) is True


def test_mock_approval_client_rejects(rejecting_client: MockApprovalClient) -> None:
    request_id = rejecting_client.request_approval("transfer_funds", "{}")
    assert rejecting_client.wait_for_approval(request_id) is False
