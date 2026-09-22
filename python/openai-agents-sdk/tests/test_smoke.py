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
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError, match="deny_destructive_data_ops"):
        handler.on_tool_start(
            serialized={"name": "delete_record"},
            input_str='{"record_id": "rec-001"}',
            run_id=run_id,
        )


def test_drop_table_is_denied(handler: AssemblyCallbackHandler) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "drop_table"},
            input_str='{"table": "users"}',
            run_id=run_id,
        )


def test_send_message_requires_approval_and_is_denied_offline(
    handler: AssemblyCallbackHandler,
) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError, match="no approver is available"):
        handler.on_tool_start(
            serialized={"name": "send_message_to_user"},
            input_str='{"user_id": "u-001", "message": "Hello"}',
            run_id=run_id,
        )


def test_trigger_payment_also_requires_approval(
    handler: AssemblyCallbackHandler,
) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "trigger_payment"},
            input_str='{"amount": 100, "currency": "USD"}',
            run_id=run_id,
        )


def test_unknown_safe_tool_is_allowed(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "list_agents"},
        input_str="{}",
        run_id=uuid4(),
    )


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
            agent_id="test-openai-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-openai-agent"
        finally:
            ctx.shutdown()
