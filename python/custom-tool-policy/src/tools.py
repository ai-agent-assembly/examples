"""Plain Python tool functions for the custom-tool-policy example.

No framework is required. Each function is a regular Python callable that
is wrapped with governance via the ``governed()`` helper in policy.py.

  - compute_sum      — safe arithmetic (ALLOWED)
  - fetch_stock_price — safe read-only query (ALLOWED)
  - send_http_request — network egress tool (DENIED by policy)
  - write_to_disk    — filesystem write tool (DENIED by policy)
"""
from __future__ import annotations


def compute_sum(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def fetch_stock_price(ticker: str) -> str:
    """Return the current stock price for a ticker symbol.

    Returns mock data in offline / demo mode.
    """
    prices = {"AAPL": 211.30, "GOOG": 178.52, "MSFT": 430.00}
    price = prices.get(ticker.upper(), 42.00)
    return f"${price:.2f} (mock)"


def send_http_request(url: str, method: str = "GET") -> str:
    """Send an HTTP request to an external URL.

    This tool is DANGEROUS (network egress) and is blocked by policy.
    """
    return f"{method} {url} → 200 OK"


def write_to_disk(path: str, content: str) -> str:
    """Write content to a file on disk.

    This tool is DANGEROUS (filesystem write) and is blocked by policy.
    """
    return f"Wrote {len(content)} bytes to {path}"
