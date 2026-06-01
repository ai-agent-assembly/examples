"""Approval workflow engine for the approval-gates scenario.

Demonstrates the pending → approved → executed flow using a local mock
instead of a real approval service.

The SDK's ``AssemblyCallbackHandler`` natively supports a three-state
decision model:

  - ``allow``   — tool runs immediately
  - ``pending`` — SDK calls ``interceptor.wait_for_tool_approval()``; runs if approved
  - ``deny``    — SDK raises ``ToolExecutionBlockedError`` immediately

``ApprovalPolicyEngine`` returns ``pending`` for ``approval_required`` rules,
then implements ``wait_for_tool_approval()`` which the SDK calls automatically.

In production, replace ``MockApprovalClient`` with the Agent Assembly
gateway-backed client:

    with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
        # ctx.client handles approval_required decisions via the gateway
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

_POLICY_FILE = Path(__file__).parent.parent.parent / "policy.yaml"


def load_policy(path: Path = _POLICY_FILE) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


class MockApprovalClient:
    """Simulates an approval service that auto-approves every request.

    In production this would send a Slack message / webhook and wait for
    a human to click Approve/Deny before returning.
    """

    def __init__(self, auto_approve: bool = True) -> None:
        self._auto_approve = auto_approve
        self._counter = 0

    def request_approval(self, tool_name: str, context: str) -> str:
        """Submit an approval request and return a request ID."""
        self._counter += 1
        request_id = f"mock-req-{self._counter:03d}"
        print(f"     ⏳ PENDING  — approval required for {tool_name!r}")
        return request_id

    def wait_for_approval(self, request_id: str) -> bool:
        """Block until the approval decision is made (mock: immediate)."""
        time.sleep(0.05)  # simulate network round-trip
        if self._auto_approve:
            print(f"     ✅ APPROVED — MockApprovalClient auto-approved (request_id={request_id!r})")
            return True
        print(f"     ❌ REJECTED — MockApprovalClient rejected (request_id={request_id!r})")
        return False


class ApprovalPolicyEngine:
    """Policy engine supporting allow, deny, and approval_required actions.

    Integrates with the SDK's native pending/wait_for_tool_approval flow:
    - ``check_tool_start`` returns ``{"status": "pending"}`` for approval_required tools
    - ``wait_for_tool_approval`` is called automatically by the SDK after a pending decision
    """

    def __init__(
        self,
        approval_client: MockApprovalClient,
        policy_path: Path = _POLICY_FILE,
    ) -> None:
        data = load_policy(policy_path)
        self._rules: dict[str, dict[str, str]] = {
            rule["tool"]: {"action": rule["action"], "reason": rule["reason"]}
            for rule in data.get("rules", [])
        }
        self._default_action: str = data.get("default_action", "deny")
        self._default_reason: str = data.get(
            "default_reason", "Unlisted tool — denied by default"
        )
        self._approval_client = approval_client
        # Tracks the active approval request ID between check_tool_start and wait_for_tool_approval
        self._pending_request_id: str | None = None
        self._pending_tool_name: str | None = None

    @property
    def rules(self) -> dict[str, dict[str, str]]:
        return self._rules

    @property
    def default_action(self) -> str:
        return self._default_action

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")
        rule = self._rules.get(
            tool_name,
            {"action": self._default_action, "reason": self._default_reason},
        )
        action = rule["action"]

        if action == "allow":
            return {"status": "allow", "reason": rule["reason"]}
        elif action == "approval_required":
            request_id = self._approval_client.request_approval(tool_name, input_str)
            self._pending_request_id = request_id
            self._pending_tool_name = tool_name
            return {"status": "pending", "reason": rule["reason"]}
        else:
            return {"status": "deny", "reason": rule["reason"]}

    def wait_for_tool_approval(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Called by the SDK after check_tool_start returns pending.

        Returns allow if approved, deny if rejected.
        """
        request_id = self._pending_request_id or "unknown"
        approved = self._approval_client.wait_for_approval(request_id)
        self._pending_request_id = None
        self._pending_tool_name = None
        if approved:
            return {"status": "allow", "reason": f"Approved (request_id={request_id!r})"}
        return {"status": "deny", "reason": "Approval request was rejected"}


def governed(tool_name: str, fn: Any, policy: ApprovalPolicyEngine) -> Any:
    """Wrap a plain Python function with approval-aware governance."""
    handler = AssemblyCallbackHandler(interceptor=policy)

    def _wrapper(**kwargs: Any) -> Any:
        handler.on_tool_start(
            serialized={"name": tool_name, "type": "tool"},
            input_str=json.dumps(kwargs, default=str),
            run_id=uuid4(),
        )
        return fn(**kwargs)

    _wrapper.__name__ = tool_name
    return _wrapper
