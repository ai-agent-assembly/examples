"""
crewai-research-crew: an Agent Assembly governance demo with a CrewAI-style
multi-agent research crew.

Three agents — a researcher, a writer, and a critic — collaborate on a research
task. The researcher delegates drafting to the writer, who delegates review to
the critic. Every governed tool call is intercepted by Agent Assembly and
attributed to the acting agent, with the full delegation chain captured on each
audit event. The crew policy:

    - requires APPROVAL if any agent attempts a file write
    - caps spend across all three agents at $2.00 / day (shared budget)
    - records every call as an AuditEvent with a delegation call stack

Run (offline mock mode — no crewai, no API keys, what CI runs):
    uv run python src/main.py --mock

For the live CrewAI integration:
    pip install -e '.[live]'
    OPENAI_API_KEY=sk-... AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \\
    uv run python src/main.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_assembly import init_assembly
from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

from src.crew import CREW, MOCK_TRAJECTORY
from src.policy import DAILY_BUDGET_USD, CrewPolicyEngine, MockApprover


def _run_delegated_call(
    handler: AssemblyCallbackHandler,
    policy: CrewPolicyEngine,
    agent: str,
    parent: str | None,
    tool: str,
    tool_input: dict[str, str],
) -> None:
    delegated = f"  (delegated by {parent})" if parent else "  (crew entry agent)"
    print(f"  [{agent}]{delegated}")
    print(f"    → {tool}({json.dumps(tool_input)})")
    policy.acting_as(agent, parent)
    try:
        handler.on_tool_start(
            serialized={"name": tool, "type": "tool"},
            input_str=json.dumps(tool_input),
            run_id=uuid4(),
        )
        print("       ✅ ALLOWED")
    except ToolExecutionBlockedError as exc:
        print(f"       ❌ BLOCKED  — {exc}")
    print()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run the offline mock crew trajectory (no crewai, CI-safe).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mock = args.mock or not os.environ.get("OPENAI_API_KEY")

    print("=" * 64)
    print("  Agent Assembly — CrewAI Multi-Agent Research Crew")
    print("=" * 64)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")
    mode_label = "mock (offline)" if mock else "live"

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="crewai-research-crew",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} ({mode_label})")
        print()

        print("Crew members:")
        for member in CREW:
            print(f"  • {member.name:<11} — {member.role}")
        print()

        print("Crew policy (local simulation of gateway policy):")
        print("  APPROVAL — any agent attempting a file write must be approved")
        print(f"  BUDGET   — ${DAILY_BUDGET_USD:.2f} / day, shared across all agents")
        print("  TRACK    — every call recorded with its delegation call stack")
        print()

        policy = CrewPolicyEngine(approver=MockApprover(auto_approve=False))
        handler = AssemblyCallbackHandler(interceptor=policy)

        print("Running crew delegation trajectory:")
        print("-" * 46)
        for step in MOCK_TRAJECTORY:
            _run_delegated_call(
                handler, policy, step.agent, step.parent, step.tool, step.tool_input
            )

        print("Delegation-aware audit events recorded this run:")
        print("-" * 46)
        for event in policy.audit_events:
            chain = _format_chain(event.call_stack)
            marker = "✅" if event.decision == "allow" else "❌"
            print(
                f"  {marker} {event.decision:<5} {event.action_type:<15} "
                f"chain: {chain}"
            )
        print()
        print(f"Final crew budget: {policy.budget.status()}")

    print()
    print("Assembly context shut down.")


def _format_chain(stack: list) -> str:
    """Render a delegation call stack as 'parent → agent → tool'."""
    labels: list[str] = []

    def _walk(nodes: list) -> None:
        for node in nodes:
            labels.append(node.label)
            _walk(node.children)

    _walk(stack)
    return " → ".join(labels)


if __name__ == "__main__":
    main()
