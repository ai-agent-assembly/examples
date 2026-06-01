#!/usr/bin/env python3
"""
Audit-trace scenario — Agent Assembly examples

Demonstrates how Agent Assembly records audit events for governed tool calls.
No API keys or external services are required to run this example.

Usage:
    python agent.py
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Minimal Agent Assembly SDK stubs used in this offline example.
# In a real integration replace these with:
#   from agent_assembly import AssemblyClient, AuditLogger
# ---------------------------------------------------------------------------


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class AuditRecord:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    agent_id: str = ""
    tool: str = ""
    decision: str = ""
    reason: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class AuditLogger:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)
        print(
            f"[AUDIT] {record.timestamp}"
            f"  tool={record.tool:<20}"
            f"  decision={record.decision:<18}"
            f"  reason={record.reason}"
        )

    def records(self) -> list[AuditRecord]:
        return list(self._records)


_POLICY: dict[str, tuple[Decision, str]] = {
    "read_file": (Decision.ALLOW, "read operations are permitted by default"),
    "delete_file": (Decision.DENY, "destructive operations are blocked by policy"),
    "send_email": (
        Decision.APPROVAL_REQUIRED,
        "outbound communication requires human approval",
    ),
}


class AssemblyClient:
    """Simulates the Agent Assembly governed runtime."""

    def __init__(self, agent_id: str, logger: AuditLogger) -> None:
        self.agent_id = agent_id
        self._logger = logger

    def call_tool(self, tool: str, **inputs: Any) -> dict[str, Any]:
        decision, reason = _POLICY.get(tool, (Decision.ALLOW, "no matching policy rule"))

        record = AuditRecord(
            agent_id=self.agent_id,
            tool=tool,
            decision=decision.value,
            reason=reason,
            inputs=inputs,
        )

        if decision is Decision.ALLOW:
            outputs: dict[str, Any] = {"status": "ok", "data": f"<result of {tool}>"}
            record.outputs = outputs
            self._logger.append(record)
            return outputs

        self._logger.append(record)

        if decision is Decision.DENY:
            raise PermissionError(f"Tool '{tool}' denied: {reason}")

        raise PermissionError(
            f"Tool '{tool}' requires approval before proceeding: {reason}"
        )


# ---------------------------------------------------------------------------
# Example agent
# ---------------------------------------------------------------------------


def run() -> None:
    print("=== Agent Assembly — Audit / Trace Example ===\n")

    audit = AuditLogger()
    client = AssemblyClient(agent_id="example-agent-001", logger=audit)

    calls: list[tuple[str, dict[str, Any]]] = [
        ("read_file", {"path": "/data/report.csv"}),
        ("delete_file", {"path": "/data/important.csv"}),
        ("send_email", {"to": "team@example.com", "subject": "Quarterly Report"}),
    ]

    print("--- Calling governed tools ---\n")

    for tool, kwargs in calls:
        args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"  → {tool}({args_str})")
        try:
            result = client.call_tool(tool, **kwargs)
            print(f"    ✓ allowed  →  {result}\n")
        except PermissionError as exc:
            print(f"    ✗ blocked  →  {exc}\n")

    print("\n--- Full audit trace (JSON) ---\n")
    for record in audit.records():
        print(record.as_json())
        print()

    print(f"Total events recorded: {len(audit.records())}")


if __name__ == "__main__":
    run()
