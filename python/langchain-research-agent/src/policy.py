"""Balanced governance policy for the langchain-research-agent example.

In production, Agent Assembly's gateway enforces these rules server-side.
This module simulates that governance layer locally so the ReAct demo runs
fully offline (``--mock``) without a running gateway or any API keys.

The "balanced" policy bundles four controls that a research agent typically
needs:

  1. Network allowlist  — outbound HTTP is only allowed to ``*.openai.com``.
  2. Daily budget        — tool calls are metered against a ``$1.00 / day`` cap.
  3. Tool-call logging   — every governed call is recorded as an audit event.
  4. Credential-leak block — any tool input carrying a secret is denied.

Production setup::

    with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
        # Policy rules (allowlist, budget, redaction) are configured in the
        # gateway; ``ctx.client`` enforces them automatically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Balanced policy configuration (mirrors gateway policy.yaml in production)
# ---------------------------------------------------------------------------

#: Outbound network egress is only permitted to hosts matching this allowlist.
NETWORK_ALLOWLIST: tuple[str, ...] = ("*.openai.com", "openai.com")

#: Per-day spend ceiling, in USD. Tool calls are metered against this cap.
DAILY_BUDGET_USD: float = 1.00

#: Per-call cost model (USD) used to meter spend in offline mode.
TOOL_COSTS: dict[str, float] = {
    "web_search": 0.02,
    "calculator": 0.00,
}

#: Patterns that indicate a credential is leaking through a tool input.
_CREDENTIAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),          # OpenAI-style secret key
    re.compile(r"AKIA[0-9A-Z]{16}"),             # AWS access key id
    re.compile(r"(?i)\bapi[_-]?key\b\s*[=:]\s*\S+"),
    re.compile(r"(?i)\b(secret|password|token)\b\s*[=:]\s*\S+"),
)


def _host_allowed(host: str) -> bool:
    """Return True if ``host`` matches an entry in :data:`NETWORK_ALLOWLIST`."""
    for entry in NETWORK_ALLOWLIST:
        if entry.startswith("*."):
            suffix = entry[1:]  # ".openai.com"
            if host == entry[2:] or host.endswith(suffix):
                return True
        elif host == entry:
            return True
    return False


def _extract_host(url: str) -> str:
    """Extract the hostname from a URL without importing urllib for one field."""
    stripped = re.sub(r"^[a-zA-Z]+://", "", url)
    return stripped.split("/", 1)[0].split(":", 1)[0].lower()


def _contains_credential(text: str) -> bool:
    return any(pattern.search(text) for pattern in _CREDENTIAL_PATTERNS)


@dataclass
class BudgetTracker:
    """Meters cumulative spend against the daily budget cap."""

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


class BalancedPolicyEngine:
    """Simulates Agent Assembly's balanced governance policy in offline mode.

    ``check_tool_start`` returns an allow / deny decision that mirrors the
    gateway wire format. The :class:`AssemblyCallbackHandler` reads these
    decisions and raises ``ToolExecutionBlockedError`` on a deny.

    Every call — allowed or denied — is appended to :attr:`audit_log` so the
    demo can replay the governance events at the end of the run.
    """

    def __init__(self, daily_budget_usd: float = DAILY_BUDGET_USD) -> None:
        self.budget = BudgetTracker(max_cost=daily_budget_usd)
        self.audit_log: list[dict[str, str]] = []

    def _record(self, tool_name: str, decision: str, reason: str) -> None:
        self.audit_log.append(
            {"tool": tool_name, "decision": decision, "reason": reason}
        )

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")

        # 4. Credential-leak block — highest priority, fail closed.
        if _contains_credential(input_str):
            reason = (
                f"Tool '{tool_name}' input contains a credential and is blocked "
                "by policy rule 'block_credential_leak'."
            )
            self._record(tool_name, "deny", reason)
            return {"status": "deny", "reason": reason}

        # 1. Network allowlist — deny egress to non-allowlisted hosts.
        match = re.search(r"https?://[^\s\"']+", input_str)
        if match:
            host = _extract_host(match.group(0))
            if not _host_allowed(host):
                reason = (
                    f"Tool '{tool_name}' attempted egress to '{host}', which is "
                    "not on the network allowlist (*.openai.com)."
                )
                self._record(tool_name, "deny", reason)
                return {"status": "deny", "reason": reason}

        # 2. Daily budget — deny once the per-day cap is exhausted.
        cost = TOOL_COSTS.get(tool_name, 0.01)
        if not self.budget.can_afford(cost):
            reason = (
                f"Tool '{tool_name}' costs ${cost:.2f} but the daily budget is "
                f"exhausted ({self.budget.status()})."
            )
            self._record(tool_name, "deny", reason)
            return {"status": "deny", "reason": reason}

        # 3. Tool-call logging — charge budget and record the allow decision.
        self.budget.charge(cost)
        reason = f"allowed (charged ${cost:.2f}; {self.budget.status()})"
        self._record(tool_name, "allow", reason)
        return {"status": "allow", "reason": reason}
