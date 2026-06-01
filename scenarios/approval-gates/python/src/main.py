"""
approval-gates: Agent Assembly approval workflow demo.

Shows how a tool that requires human approval is paused, reviewed, and then
executed after the mock approver grants permission.

Run:
    uv run python src/main.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.approval import ApprovalPolicyEngine, MockApprovalClient, governed
from src.tools import get_balance, transfer_funds

_DEMO_CALLS: list[tuple[str, dict]] = [
    ("get_balance", {"account_id": "acc-001"}),
    ("transfer_funds", {"from_account": "acc-001", "to_account": "acc-002", "amount": 500.0}),
]


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Approval Gates Scenario")
    print("=" * 62)
    print()

    approval_client = MockApprovalClient(auto_approve=True)
    policy = ApprovalPolicyEngine(approval_client)

    print(f"Policy loaded from policy.yaml  ({len(policy.rules)} rules, default: {policy.default_action})")
    for name, rule in policy.rules.items():
        action_label = rule["action"].upper().replace("_", "_")
        print(f"  {action_label:<18} {name:<14} — {rule['reason']}")
    print()

    raw_fns = {
        "get_balance": get_balance,
        "transfer_funds": transfer_funds,
    }
    tools = {name: governed(name, fn, policy) for name, fn in raw_fns.items()}

    print("Running governed tool calls:")
    print("-" * 44)
    succeeded = 0
    for tool_name, kwargs in _DEMO_CALLS:
        args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"  → {tool_name}({args_str})")
        try:
            result = tools[tool_name](**kwargs)
            print(f"     ✅ EXECUTED — {result}")
            succeeded += 1
        except ToolExecutionBlockedError as exc:
            print(f"     ❌ BLOCKED  — {exc}")
        print()

    immediate = sum(1 for n, _ in _DEMO_CALLS if policy.rules.get(n, {}).get("action") == "allow")
    via_approval = succeeded - immediate
    print(f"{len(_DEMO_CALLS)} tool calls: {succeeded} succeeded ({immediate} immediate, {via_approval} via approval).")


if __name__ == "__main__":
    main()
