"""Smoke tests for custom-tool-policy — fully offline, no gateway or framework needed."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed
from src.tools import compute_sum, fetch_stock_price, send_http_request, write_to_disk


@pytest.fixture
def policy() -> LocalPolicyEngine:
    return LocalPolicyEngine()


def test_compute_sum_is_allowed(policy: LocalPolicyEngine) -> None:
    fn = governed("compute_sum", compute_sum, policy)
    assert fn(a=3.0, b=4.0) == 7.0


def test_fetch_stock_price_is_allowed(policy: LocalPolicyEngine) -> None:
    fn = governed("fetch_stock_price", fetch_stock_price, policy)
    result = fn(ticker="AAPL")
    assert "$" in result


def test_send_http_request_is_denied(policy: LocalPolicyEngine) -> None:
    fn = governed("send_http_request", send_http_request, policy)
    with pytest.raises(ToolExecutionBlockedError, match="deny_network_and_disk_writes"):
        fn(url="https://example.com", method="GET")


def test_write_to_disk_is_denied(policy: LocalPolicyEngine) -> None:
    fn = governed("write_to_disk", write_to_disk, policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(path="/etc/passwd", content="evil")


def test_denied_fn_body_never_executes(policy: LocalPolicyEngine) -> None:
    called = []
    fn = governed("send_http_request", lambda url, method="GET": called.append(url), policy)
    with pytest.raises(ToolExecutionBlockedError):
        fn(url="https://example.com")
    assert called == [], "blocked tool function must not execute"


def test_unknown_tool_name_is_allowed(policy: LocalPolicyEngine) -> None:
    fn = governed("read_file", lambda path: f"contents of {path}", policy)
    result = fn(path="/tmp/safe.txt")
    assert "contents" in result


def test_init_assembly_sdk_only_requires_no_gateway() -> None:
    from agent_assembly import init_assembly
    from agent_assembly.core import assembly as _core

    with patch.object(_core, "_register_adapters", return_value=[]):
        with patch.object(
            _core, "_start_network_layer", return_value=("sdk-only", lambda: None)
        ):
            ctx = init_assembly(
                gateway_url="http://localhost:8080",
                agent_id="test-custom-agent",
                mode="sdk-only",
            )
            try:
                assert ctx.client.agent_id == "test-custom-agent"
            finally:
                ctx.shutdown()
