"""
custom-tool-policy: Agent Assembly governance with plain Python functions.

The simplest possible Agent Assembly integration — no AI framework required.
Demonstrates how governance wraps any Python callable using the ``governed()``
helper from policy.py.

Run (fully offline, no gateway or API key):
    uv run python src/main.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.policy import LocalPolicyEngine, governed
from src.tools import (
    compute_sum,
    fetch_stock_price,
    send_http_request,
    write_to_disk,
)

_DEMO_CALLS: list[tuple[str, dict]] = [
    ("compute_sum", {"a": 12.5, "b": 7.3}),
    ("fetch_stock_price", {"ticker": "AAPL"}),
    ("send_http_request", {"url": "https://example.com/data", "method": "POST"}),
    ("write_to_disk", {"path": "/etc/cron.d/evil", "content": "rm -rf /"}),
]


def main() -> None:
    print("=" * 62)
    print("  Agent Assembly — Custom Tool Policy Demo")
    print("  (no AI framework required)")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="custom-tool-demo-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} (offline demo)")
        print()

        policy = LocalPolicyEngine()

        raw_fns = {
            "compute_sum": compute_sum,
            "fetch_stock_price": fetch_stock_price,
            "send_http_request": send_http_request,
            "write_to_disk": write_to_disk,
        }
        tools = {name: governed(name, fn, policy) for name, fn in raw_fns.items()}

        print("Policy rules (local simulation of gateway policy):")
        print("  DENY   — send_http_request, write_to_disk  (network / disk writes)")
        print("  ALLOW  — everything else")
        print()

        print("Running governed tool calls:")
        print("-" * 44)
        for tool_name, kwargs in _DEMO_CALLS:
            print(f"  → {tool_name}({kwargs})")
            try:
                result = tools[tool_name](**kwargs)
                print(f"     ✅ ALLOWED  — {result}")
            except ToolExecutionBlockedError as exc:
                print(f"     ❌ BLOCKED  — {exc}")
            print()

    print("Assembly context shut down.")


if __name__ == "__main__":
    main()
