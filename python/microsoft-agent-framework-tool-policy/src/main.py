"""microsoft-agent-framework-governed-agent: Agent Assembly + Microsoft Agent Framework.

This example shows how Agent Assembly intercepts Microsoft Agent Framework tool
calls and enforces policy before any tool executes.

It runs **two ways**, mirroring the rest of this gallery:

- ``--mock`` (the default, what CI runs): replays the three governed tool calls
  through the ``LocalPolicyEngine`` decision contract **without importing the
  heavy ``agent_framework`` package** — proving the allow / deny / pending policy
  outcomes offline with only the SDK + ``dev`` deps installed.
- ``live`` (no flag): drives the **real** ``agent_framework.FunctionTool.invoke``
  through the installed ``MicrosoftAgentFrameworkAdapter`` — the exact call an
  Agent Framework agent makes to run a tool — so a denied tool is short-circuited
  by the patched ``invoke`` before its body runs. Needs the ``live`` extra
  (``uv sync --extra live --prerelease=allow``).

Run (offline mock mode — no agent-framework, no API keys, what CI runs):
    uv run python src/main.py --mock

For the live Microsoft Agent Framework integration:
    uv sync --extra live --prerelease=allow
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 uv run python src/main.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.microsoft_agent_framework import (
    MicrosoftAgentFrameworkAdapter,
)
from agent_assembly.exceptions import PolicyViolationError

from src.policy import LocalPolicyEngine

_DEMO_CALLS: list[str] = ["get_weather", "delete_records", "send_email"]


async def _decide(policy: LocalPolicyEngine, tool_name: str) -> tuple[str, str]:
    """Resolve the policy outcome for *tool_name* via the governance hook contract.

    Mirrors what the adapter does on a real ``invoke``: ``check_tool_start`` first,
    then ``wait_for_tool_approval`` for a ``pending`` verdict.
    """
    decision = await policy.check_tool_start(tool_name=tool_name)
    status = decision["status"]
    if status == "pending":
        decision = await policy.wait_for_tool_approval(tool_name=tool_name)
        status = decision["status"]
    return status, decision.get("reason", "")


async def _run_mock(policy: LocalPolicyEngine) -> None:
    print("Running governed tool calls (mock — policy contract, offline):")
    print("-" * 44)
    for tool_name in _DEMO_CALLS:
        print(f"  → invoke tool {tool_name}")
        status, reason = await _decide(policy, tool_name)
        if status == "allow":
            print(f"     ✅ ALLOWED  — {tool_name} would execute")
        else:
            print(f"     ❌ BLOCKED  — {reason}")
        print()


async def _run_live() -> None:
    # Imported lazily: the real framework is only needed for the live path so the
    # mock path (and CI's `dev`-only install) never pulls the heavy package.
    from src.tools import build_tools, tool_arguments

    tools = build_tools()
    print("Running governed tool calls (live — FunctionTool.invoke):")
    print("-" * 44)
    for tool_name in _DEMO_CALLS:
        print(f"  → invoke tool {tool_name}")
        try:
            await tools[tool_name].invoke(arguments=tool_arguments(tool_name))
            print(f"     ✅ ALLOWED  — {tool_name} executed (mock response)")
        except PolicyViolationError as exc:
            print(f"     ❌ BLOCKED  — {exc}")
        print()


async def _run_demo(*, mock: bool) -> None:
    print("=" * 62)
    print("  Agent Assembly — Microsoft Agent Framework Governed Agent Demo")
    print("=" * 62)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")
    mode_label = "mock" if mock else "live"

    print(
        f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode, {mode_label})..."
    )

    # region: quickstart
    policy = LocalPolicyEngine()

    # Live path: install the governance hooks BEFORE init_assembly. The adapter
    # patches `agent_framework.FunctionTool.invoke`; because the patch is
    # idempotent, registering first makes init_assembly's auto-detection a no-op
    # and keeps the offline `LocalPolicyEngine` wired as the interceptor (rather
    # than the no-op interceptor auto-detection would install).
    adapter: MicrosoftAgentFrameworkAdapter | None = None
    if not mock:
        adapter = MicrosoftAgentFrameworkAdapter()
        adapter.set_process_agent_id("microsoft-agent-framework-demo-agent")
        adapter.register_hooks(policy)

    try:
        with init_assembly(
            gateway_url=gateway_url,
            api_key=api_key,
            agent_id="microsoft-agent-framework-demo-agent",
            mode="sdk-only",
        ) as ctx:
            # endregion
            print(f"  Agent:    {ctx.client.agent_id}")
            print(f"  Gateway:  {ctx.client.gateway_url}")
            print(f"  Mode:     {ctx.network_mode} (offline demo)")
            print()

            print("Policy rules (local simulation of gateway policy):")
            print("  DENY    — delete_records, write_file  (destructive operations)")
            print("  PENDING — send_email                  (requires human approval)")
            print("  ALLOW   — everything else")
            print()

            if mock:
                await _run_mock(policy)
            else:
                await _run_live()
    finally:
        if adapter is not None:
            adapter.unregister_hooks()

    print("Assembly context shut down.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run offline without importing agent-framework (the default CI path).",
    )
    args = parser.parse_args()
    asyncio.run(_run_demo(mock=args.mock))


if __name__ == "__main__":
    main()
