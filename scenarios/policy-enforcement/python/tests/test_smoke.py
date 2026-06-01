"""Smoke tests for the policy-enforcement scenario — offline, no gateway."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed, load_policy
from src.tools import delete_agent, list_agents, read_config, send_email


@pytest.fixture
def policy() -> LocalPolicyEngine:
    return LocalPolicyEngine()


def test_policy_yaml_loads() -> None:
    data = load_policy()
    assert "rules" in data
    assert len(data["rules"]) >= 4
    assert data.get("default_action") == "deny"


def test_read_config_is_allowed(policy: LocalPolicyEngine) -> None:
    fn = governed("read_config", read_config, policy)
    result = fn(key="database.host")
    assert "localhost" in result


def test_list_agents_is_allowed(policy: LocalPolicyEngine) -> None:
    fn = governed("list_agents", list_agents, policy)
    result = fn()
    assert isinstance(result, list)
    assert len(result) > 0


def test_delete_agent_is_denied(policy: LocalPolicyEngine) -> None:
    fn = governed("delete_agent", delete_agent, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(agent_id="agent-001")


def test_send_email_is_denied(policy: LocalPolicyEngine) -> None:
    fn = governed("send_email", send_email, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(to="admin@example.com", subject="Hi", body="Test")


def test_denied_body_never_executes(policy: LocalPolicyEngine) -> None:
    called: list[str] = []
    fn = governed("delete_agent", lambda agent_id: called.append(agent_id), policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(agent_id="target")
    assert called == [], "blocked tool body must not execute"


def test_unknown_tool_uses_default_deny(policy: LocalPolicyEngine) -> None:
    fn = governed("execute_shell", lambda cmd: cmd, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(cmd="rm -rf /")


def test_policy_rules_contain_expected_tools(policy: LocalPolicyEngine) -> None:
    assert "read_config" in policy.rules
    assert "list_agents" in policy.rules
    assert "delete_agent" in policy.rules
    assert "send_email" in policy.rules
    assert policy.rules["read_config"]["action"] == "allow"
    assert policy.rules["delete_agent"]["action"] == "deny"
