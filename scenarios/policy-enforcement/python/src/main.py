"""
policy-enforcement: Agent Assembly policy enforcement demo.

Shows how a shared policy.yaml file drives allow/deny decisions for every
tool call.  No gateway or API key is required — fully offline.

Run:
    uv run python src/main.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed
from src.tools import delete_agent, list_agents, read_config, send_email

_DEMO_CALLS: list[tuple[str, dict]] = [
    ("read_config", {"key": "database.host"}),
    ("list_agents", {}),
    ("delete_agent", {"agent_id": "agent-001"}),
    ("send_email", {"to": "admin@example.com", "subject": "Hello", "body": "Test message"}),
]


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Policy Enforcement Scenario")
    print("=" * 62)
    print()

    policy = LocalPolicyEngine()

    print(f"Policy loaded from policy.yaml  ({len(policy.rules)} rules, default: {policy.default_action})")
    for name, rule in policy.rules.items():
        icon = "ALLOW" if rule["action"] == "allow" else "DENY "
        print(f"  {icon}  {name:<14} — {rule['reason']}")
    print()

    raw_fns = {
        "read_config": read_config,
        "list_agents": list_agents,
        "delete_agent": delete_agent,
        "send_email": send_email,
    }
    tools = {name: governed(name, fn, policy) for name, fn in raw_fns.items()}

    print("Running governed tool calls:")
    print("-" * 44)
    allowed = denied = 0
    for tool_name, kwargs in _DEMO_CALLS:
        args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"  → {tool_name}({args_str})")
        try:
            result = tools[tool_name](**kwargs)
            print(f"     ✅ ALLOWED  — {result}")
            allowed += 1
        except ToolExecutionBlockedError as exc:
            print(f"     ❌ DENIED   — {exc}")
            denied += 1
        print()

    print(f"{allowed + denied} tool calls: {allowed} allowed, {denied} denied.")


if __name__ == "__main__":
    main()
