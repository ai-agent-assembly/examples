"""Microsoft Agent Framework tool definitions for the governed-agent example.

These are genuine ``agent_framework.FunctionTool`` instances produced by the
framework's ``@tool`` decorator — the exact objects an Agent Framework
``ChatAgent`` invokes when a model decides to call a tool. The Agent Assembly
adapter patches ``FunctionTool.invoke``, so driving ``tool.invoke(...)`` here
exercises the identical production governance path with the tool fully real and
only the chat model absent (keeping the demo offline and deterministic).

``agent_framework`` is imported lazily so the policy module stays import-safe
when the framework is not installed.
"""

from __future__ import annotations

from typing import Any


def build_tools() -> dict[str, Any]:
    """Return the demo's governed ``FunctionTool`` instances, keyed by name.

    Each tool's body is a simple side-effecting stub; the point of the demo is
    that an *allowed* tool's body runs while a *denied* one is short-circuited by
    the governance hook before its body executes.
    """
    import agent_framework as af

    # `agent_framework` ships no type stubs, so `af.tool` is an untyped (`Any`)
    # decorator; the scoped ignore is the genuine framework limitation, not a
    # real typing defect.
    @af.tool  # type: ignore[untyped-decorator]
    def get_weather(city: str) -> str:
        """Get the current weather for a city (safe — allowed by policy)."""
        return f"Weather in {city}: 22C, partly cloudy (mock response)"

    @af.tool  # type: ignore[untyped-decorator]
    def delete_records(path: str) -> str:
        """Delete records at a path (destructive — denied by policy)."""
        return f"Deleted records at {path}"

    @af.tool  # type: ignore[untyped-decorator]
    def send_email(to: str) -> str:
        """Send an email (requires approval — pending then denied offline)."""
        return f"Email sent to {to}"

    return {tool.name: tool for tool in (get_weather, delete_records, send_email)}


def tool_arguments(tool_name: str) -> dict[str, str]:
    """Return representative arguments for *tool_name* used to drive ``invoke``."""
    return {
        "get_weather": {"city": "Seattle"},
        "delete_records": {"path": "/var/data/customers"},
        "send_email": {"to": "ops@example.com"},
    }[tool_name]
