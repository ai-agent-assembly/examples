"""Smoke tests for llamaindex-tool-policy — offline, no gateway or API key required."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import GovernedToolRunner, LocalPolicyEngine


@pytest.fixture
def policy() -> LocalPolicyEngine:
    return LocalPolicyEngine()


def test_query_index_is_allowed(policy: LocalPolicyEngine) -> None:
    runner = GovernedToolRunner("query_index", lambda query: f"results for {query}", policy)
    result = runner.run(query="agent assembly docs")
    assert "results for" in result


def test_summarize_docs_is_allowed(policy: LocalPolicyEngine) -> None:
    runner = GovernedToolRunner("summarize_docs", lambda topic: f"summary of {topic}", policy)
    result = runner.run(topic="governance")
    assert "summary of" in result


def test_execute_sql_is_denied(policy: LocalPolicyEngine) -> None:
    runner = GovernedToolRunner("execute_sql", lambda sql: "rows", policy)
    with pytest.raises(ToolExecutionBlockedError, match="deny_arbitrary_execution"):
        runner.run(sql="SELECT * FROM secrets")


def test_run_shell_command_is_denied(policy: LocalPolicyEngine) -> None:
    runner = GovernedToolRunner("run_shell_command", lambda cmd: "output", policy)
    with pytest.raises(ToolExecutionBlockedError):
        runner.run(cmd="rm -rf /")


def test_unknown_tool_is_allowed(policy: LocalPolicyEngine) -> None:
    runner = GovernedToolRunner("list_indexes", lambda: "idx-1, idx-2", policy)
    result = runner.run()
    assert "idx" in result


def test_governed_runner_does_not_call_fn_when_denied(policy: LocalPolicyEngine) -> None:
    called = []
    runner = GovernedToolRunner("execute_sql", lambda sql: called.append(sql), policy)
    with pytest.raises(ToolExecutionBlockedError):
        runner.run(sql="DROP TABLE users")
    assert called == [], "fn must not be called when governance denies"


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-llamaindex-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-llamaindex-agent"
            finally:
                ctx.shutdown()
