"""Pydantic AI agent definition for the pydantic-ai-governed-agent example.

The agent is wired with ``TestModel`` — Pydantic AI's built-in offline model —
so it runs deterministically with **no API key and no network**. ``TestModel``
is told which tool to call, which lets the demo exercise the allow / deny /
pending governance paths the Agent Assembly adapter installs on Pydantic AI's
tool-execution path (``AbstractToolset.call_tool`` on >=0.3.0, ``Tool._run`` on
<0.3.0).
"""
from __future__ import annotations

from typing import Any


def build_agent(call_tool: str) -> Any:
    """Build a Pydantic AI agent that deterministically calls ``call_tool``.

    Importing ``pydantic_ai`` lazily keeps the policy module import-safe even
    when the framework is not installed.
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    agent = Agent(TestModel(call_tools=[call_tool]))

    @agent.tool_plain
    def get_weather(city: str) -> str:
        """Get the current weather for a city (safe — allowed by policy)."""
        return f"Weather in {city}: 22C, partly cloudy (mock response)"

    @agent.tool_plain
    def delete_records(path: str) -> str:
        """Delete records at a path (destructive — denied by policy)."""
        return f"Deleted records at {path}"

    @agent.tool_plain
    def send_email(to: str) -> str:
        """Send an email (requires approval — pending then denied offline)."""
        return f"Email sent to {to}"

    return agent
