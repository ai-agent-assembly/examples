"""Smoke tests for langchain-basic-agent — offline, no gateway required."""
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


def test_allowed_tool_passes(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "get_weather"},
        input_str='{"city": "Tokyo"}',
        run_id=uuid4(),
    )


def test_denied_tool_raises_blocked(handler: AssemblyCallbackHandler) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError, match="blocked by policy rule"):
        handler.on_tool_start(
            serialized={"name": "delete_files"},
            input_str='{"path": "/etc/passwd"}',
            run_id=run_id,
        )


def test_write_file_also_denied(handler: AssemblyCallbackHandler) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError):
        handler.on_tool_start(
            serialized={"name": "write_file"},
            input_str='{"path": "/etc/cron.d/evil", "content": "rm -rf /"}',
            run_id=run_id,
        )


def test_pending_tool_denied_without_approver(handler: AssemblyCallbackHandler) -> None:
    run_id = uuid4()
    with pytest.raises(ToolExecutionBlockedError, match="no approver is available"):
        handler.on_tool_start(
            serialized={"name": "send_email"},
            input_str='{"to": "all@co.com", "subject": "Hi", "body": "World"}',
            run_id=run_id,
        )


def test_unknown_tool_is_allowed(handler: AssemblyCallbackHandler) -> None:
    handler.on_tool_start(
        serialized={"name": "search_web"},
        input_str='"agent assembly docs"',
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
            agent_id="test-langchain-agent",
            mode="sdk-only",
        )
        try:
            assert ctx.client.agent_id == "test-langchain-agent"
            assert ctx.network_mode == "sdk-only"
        finally:
            ctx.shutdown()
