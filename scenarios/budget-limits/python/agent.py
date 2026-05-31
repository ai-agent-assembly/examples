#!/usr/bin/env python3
"""
Budget-limits scenario — Agent Assembly examples

Demonstrates how Agent Assembly enforces budget guardrails on governed tool calls.
No API keys or external services are required to run this example.

Usage:
    python agent.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Per-call costs matching policy.yaml
TOOL_COSTS: dict[str, float] = {
    "web_search": 0.05,
    "query_database": 0.10,
    "call_external_api": 0.20,
    "generate_report": 0.25,
}

# Session budget ceiling matching policy.yaml budget.max_cost
BUDGET_LIMIT: float = 0.50


# ---------------------------------------------------------------------------
# Minimal Agent Assembly SDK stubs used in this offline example.
# In a real integration replace these with:
#   from agent_assembly import AssemblyClient, BudgetPolicy
# ---------------------------------------------------------------------------


class BudgetExceededError(PermissionError):
    pass


@dataclass
class BudgetTracker:
    max_cost: float
    _spent: float = field(default=0.0, init=False)

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_cost - self._spent)

    def charge(self, cost: float) -> None:
        self._spent += cost

    def status(self) -> str:
        pct = (self._spent / self.max_cost) * 100
        return f"spent=${self._spent:.2f} / limit=${self.max_cost:.2f} ({pct:.0f}%)"


class AssemblyClient:
    """Simulates the Agent Assembly governed runtime with budget enforcement."""

    def __init__(self, agent_id: str, budget: BudgetTracker) -> None:
        self.agent_id = agent_id
        self._budget = budget

    def call_tool(self, tool: str, **inputs: Any) -> dict[str, Any]:
        cost = TOOL_COSTS.get(tool, 0.01)

        if cost > self._budget.remaining:
            raise BudgetExceededError(
                f"Budget exceeded: tool '{tool}' costs ${cost:.2f} but "
                f"only ${self._budget.remaining:.2f} remains "
                f"(spent=${self._budget.spent:.2f} / limit=${self._budget.max_cost:.2f})"
            )

        self._budget.charge(cost)
        print(
            f"  [BUDGET] charged ${cost:.2f} for '{tool}'"
            f"  →  {self._budget.status()}"
        )
        return {"status": "ok", "tool": tool, "data": f"<result of {tool}>"}


# ---------------------------------------------------------------------------
# Example agent
# ---------------------------------------------------------------------------


def run() -> None:
    print("=== Agent Assembly — Budget Limits Example ===\n")
    print(f"Policy: max_cost=${BUDGET_LIMIT:.2f} per session (see policy.yaml)\n")

    budget = BudgetTracker(max_cost=BUDGET_LIMIT)
    client = AssemblyClient(agent_id="example-agent-001", budget=budget)

    calls: list[tuple[str, dict[str, Any]]] = [
        ("web_search", {"query": "latest AI news"}),          # $0.05 → $0.05
        ("query_database", {"table": "customers"}),           # $0.10 → $0.15
        ("call_external_api", {"endpoint": "/v1/report"}),    # $0.20 → $0.35
        ("web_search", {"query": "weather forecast"}),        # $0.05 → $0.40
        ("generate_report", {"format": "pdf"}),               # $0.25 → exceeds $0.50
        ("call_external_api", {"endpoint": "/v2/sync"}),      # $0.20 → blocked — not enough left
    ]

    print("--- Running tool calls against budget ---\n")

    for tool, kwargs in calls:
        cost = TOOL_COSTS.get(tool, 0.01)
        args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"  → {tool}({args_str})  [cost=${cost:.2f}]")
        try:
            result = client.call_tool(tool, **kwargs)
            print(f"    ✓ allowed  →  {result}\n")
        except BudgetExceededError as exc:
            print(f"    ✗ denied   →  {exc}\n")

    print(f"\nFinal budget state: {budget.status()}")


if __name__ == "__main__":
    run()
