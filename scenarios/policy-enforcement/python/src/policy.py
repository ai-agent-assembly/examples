"""Policy engine for the policy-enforcement scenario.

Loads allow/deny rules from ``../../policy.yaml`` (relative to this file's
directory) and applies them to every governed tool call.

In production, swap ``LocalPolicyEngine`` with the gateway-backed client:

    with init_assembly(gateway_url="http://localhost:8080", agent_id="my-agent") as ctx:
        policy = ctx.client   # gateway-backed, not a local file
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml

from agent_assembly.adapters.langchain import AssemblyCallbackHandler
from agent_assembly.exceptions import ToolExecutionBlockedError

_POLICY_FILE = Path(__file__).parent.parent.parent / "policy.yaml"


def load_policy(path: Path = _POLICY_FILE) -> dict[str, Any]:
    """Load the policy YAML file and return the parsed dict."""
    with path.open() as f:
        return yaml.safe_load(f)


class LocalPolicyEngine:
    """File-backed policy engine: evaluates tool calls against policy.yaml rules."""

    def __init__(self, policy_path: Path = _POLICY_FILE) -> None:
        data = load_policy(policy_path)
        self._rules: dict[str, dict[str, str]] = {
            rule["tool"]: {"action": rule["action"], "reason": rule["reason"]}
            for rule in data.get("rules", [])
        }
        self._default_action: str = data.get("default_action", "deny")
        self._default_reason: str = data.get(
            "default_reason", "Unlisted tool — denied by default"
        )

    @property
    def rules(self) -> dict[str, dict[str, str]]:
        return self._rules

    @property
    def default_action(self) -> str:
        return self._default_action

    def check_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        tool_name = serialized.get("name", "")
        if tool_name in self._rules:
            rule = self._rules[tool_name]
            return {"status": rule["action"], "reason": rule["reason"]}
        return {"status": self._default_action, "reason": self._default_reason}


def governed(tool_name: str, fn: Any, policy: LocalPolicyEngine) -> Any:
    """Wrap a plain Python function with governance.

    Raises ``ToolExecutionBlockedError`` when the policy denies the tool.
    """
    handler = AssemblyCallbackHandler(interceptor=policy)

    def _wrapper(**kwargs: Any) -> Any:
        handler.on_tool_start(
            serialized={"name": tool_name, "type": "tool"},
            input_str=json.dumps(kwargs, default=str),
            run_id=uuid4(),
        )
        return fn(**kwargs)

    _wrapper.__name__ = tool_name
    return _wrapper
