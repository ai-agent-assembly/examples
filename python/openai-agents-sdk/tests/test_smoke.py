"""Smoke tests for openai-agents-sdk — offline, no gateway or API key required."""
from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine


@pytest.fixture
def handler() -> AssemblyCallbackHandler:
    return AssemblyCallbackHandler(interceptor=LocalPolicyEngine())


def test_search_documents_is_allowed(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "search_documents"},
        input_str='{"query": "governance docs"}',
        run_id=uuid4(),
    )


def test_delete_record_is_denied(handler: AssemblyCallbackHandler) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="deny_destructive_data_ops"):
        handler.on_tool_start(
            serialized={"name": "delete_record"},
            input_str='{"record_id": "rec-001"}',
            run_id=uuid4(),
        )


def test_drop_table_is_denied(handler: AssemblyCallbackHandler) -> None:
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "drop_table"},
            input_str='{"table": "users"}',
            run_id=uuid4(),
        )


def test_send_message_requires_approval_and_is_denied_offline(
    handler: AssemblyCallbackHandler,
) -> None:
    with pytest.raises(ToolExecutionBlockedError, match="no approver is available"):
        handler.on_tool_start(
            serialized={"name": "send_message_to_user"},
            input_str='{"user_id": "u-001", "message": "Hello"}',
            run_id=uuid4(),
        )


def test_trigger_payment_also_requires_approval(
    handler: AssemblyCallbackHandler,
) -> None:
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "trigger_payment"},
            input_str='{"amount": 100, "currency": "USD"}',
            run_id=uuid4(),
        )


def test_unknown_safe_tool_is_allowed(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "list_agents"},
        input_str="{}",
        run_id=uuid4(),
    )


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-openai-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-openai-agent"
            finally:
                ctx.shutdown()
