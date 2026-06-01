"""Tool functions for the approval-gates scenario.

  - get_balance   — safe read-only query (ALLOWED immediately)
  - transfer_funds — risky write operation (requires APPROVAL before execution)
"""
from __future__ import annotations

_BALANCES: dict[str, float] = {
    "acc-001": 12450.00,
    "acc-002": 3200.00,
    "acc-003": 875.50,
}


def get_balance(account_id: str) -> str:
    """Return the account balance (safe, read-only)."""
    balance = _BALANCES.get(account_id, 0.00)
    return f"${balance:,.2f}"


def transfer_funds(from_account: str, to_account: str, amount: float) -> str:
    """Transfer funds between accounts (requires approval before execution)."""
    return f"Transferred ${amount:,.2f} from {from_account} to {to_account}"
