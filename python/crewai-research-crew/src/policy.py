"""Multi-agent governance policy for the crewai-research-crew example.

In production, Agent Assembly's gateway enforces these rules server-side.
This module simulates that governance layer locally so the crew demo runs
fully offline (``--mock``) without a gateway or any API keys.

The crew policy adds two controls on top of per-tool governance:

  1. File-write approval — any agent that attempts a file write is gated:
     the decision is ``pending`` and an approver must sign off.
  2. Daily budget        — tool calls across *all three* agents are metered
     against a shared ``$2.00 / day`` cap.

Because this is a multi-agent crew, every governed call is recorded as an
:class:`AuditEvent` whose ``call_stack`` captures the delegation chain
(parent agent → acting agent → tool). This is the agent-delegation tracking
that distinguishes multi-agent governance from single-agent governance.

Production setup::

    with init_assembly(gateway_url="http://localhost:8080", agent_id="crew") as ctx:
        # Approval gates and budgets are configured in the gateway; ``ctx.client``
        # enforces them and emits AuditEvents with the full delegation call stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agent_assembly.types import AuditEvent, CallStackNode

#: Shared per-day spend ceiling (USD) across every agent in the crew.
DAILY_BUDGET_USD: float = 2.00

#: Per-call cost model (USD) used to meter spend in offline mode.
TOOL_COSTS: dict[str, float] = {
    "web_search": 0.05,
    "compose_report": 0.10,
    "review_text": 0.05,
    "write_file": 0.00,
}

#: Tools that require human approval before execution.
APPROVAL_REQUIRED_TOOLS: frozenset[str] = frozenset({"write_file"})


@dataclass
class BudgetTracker:
    """Meters cumulative crew spend against the shared daily budget cap."""

    max_cost: float
    _spent: float = field(default=0.0, init=False)

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_cost - self._spent)

    def can_afford(self, cost: float) -> bool:
        return cost <= self.remaining

    def charge(self, cost: float) -> None:
        self._spent += cost

    def status(self) -> str:
        pct = (self._spent / self.max_cost * 100) if self.max_cost else 0.0
        return f"spent=${self._spent:.2f} / limit=${self.max_cost:.2f} ({pct:.0f}%)"


class MockApprover:
    """Stand-in approval service for ``write_file`` requests.

    In production this would notify a human (Slack / webhook) and block until a
    decision. Here it rejects file writes so the demo shows the crew being held
    back from persisting data without sign-off.
    """

    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve

    def decide(self, _tool_name: str, _acting_agent: str) -> bool:
        return self.auto_approve


class CrewPolicyEngine:
    """Simulates Agent Assembly's multi-agent crew policy in offline mode.

    The active crew member is tracked via :meth:`acting_as`. When the SDK calls
    ``check_tool_start`` / ``wait_for_tool_approval`` it uses that context to
    attribute the call to the right agent and to build the delegation call
    stack on the emitted :class:`AuditEvent`.
    """

    def __init__(
        self,
        approver: MockApprover | None = None,
        daily_budget_usd: float = DAILY_BUDGET_USD,
    ) -> None:
        self.budget = BudgetTracker(max_cost=daily_budget_usd)
        self.approver = approver or MockApprover(auto_approve=False)
        self.audit_events: list[AuditEvent] = []
        self._acting_agent: str = "crew"
        self._parent_agent: str | None = None

    def acting_as(self, agent: str, parent: str | None = None) -> None:
        """Set the crew member that subsequent governed calls belong to."""
        self._acting_agent = agent
        self._parent_agent = parent

    def _emit(self, tool_name: str, decision: str) -> None:
        """Record an AuditEvent whose call_stack is the delegation chain."""
        tool_node = CallStackNode(id=str(uuid4()), kind="tool", label=tool_name)
        acting_node = CallStackNode(
            id=str(uuid4()),
            kind="llm",
            label=self._acting_agent,
            children=[tool_node],
        )
        if self._parent_agent is not None:
            stack = [
                CallStackNode(
                    id=str(uuid4()),
                    kind="llm",
                    label=self._parent_agent,
                    children=[acting_node],
                )
            ]
        else:
            stack = [acting_node]

        self.audit_events.append(
            AuditEvent(
                event_id=str(uuid4()),
                agent_id=self._acting_agent,
                action_type=tool_name,
                decision=decision,
                labels={
                    "crew_member": self._acting_agent,
                    "delegated_by": self._parent_agent or "",
                },
                call_stack=stack,
            )
        )

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")

        # 1. File-write approval gate — defer to wait_for_tool_approval.
        if tool_name in APPROVAL_REQUIRED_TOOLS:
            return {
                "status": "pending",
                "reason": (
                    f"Agent '{self._acting_agent}' must obtain approval before "
                    f"'{tool_name}' (file writes require sign-off)."
                ),
            }

        # 2. Shared daily budget — deny once the crew's cap is exhausted.
        cost = TOOL_COSTS.get(tool_name, 0.01)
        if not self.budget.can_afford(cost):
            self._emit(tool_name, "deny")
            return {
                "status": "deny",
                "reason": (
                    f"Agent '{self._acting_agent}' call '{tool_name}' costs "
                    f"${cost:.2f} but the crew daily budget is exhausted "
                    f"({self.budget.status()})."
                ),
            }

        self.budget.charge(cost)
        self._emit(tool_name, "allow")
        return {
            "status": "allow",
            "reason": f"allowed for '{self._acting_agent}' "
            f"(charged ${cost:.2f}; {self.budget.status()})",
        }

    def wait_for_tool_approval(
        self,
        serialized: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, str]:
        """Called by the SDK after a ``pending`` decision on a file write."""
        tool_name = serialized.get("name", "")
        approved = self.approver.decide(tool_name, self._acting_agent)
        decision = "allow" if approved else "deny"
        self._emit(tool_name, decision)
        if approved:
            return {
                "status": "allow",
                "reason": f"Approved file write for '{self._acting_agent}'.",
            }
        return {
            "status": "deny",
            "reason": (
                f"Approval for '{tool_name}' by '{self._acting_agent}' was "
                "rejected — the crew may not persist files without sign-off."
            ),
        }
