"""LangChain tool definitions for the langchain-basic-agent example.

Three tools are defined:
  - get_weather  — safe information tool (ALLOWED by policy)
  - delete_files — destructive file tool (DENIED by policy)
  - send_email   — outbound communication tool (requires APPROVAL)
"""
from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Returns mock data in offline / demo mode.
    """
    return f"🌤  Weather in {city}: 22°C, partly cloudy (mock response)"


@tool
def delete_files(path: str) -> str:
    """Delete all files at the given filesystem path.

    This tool is DANGEROUS and is blocked by policy in this example.
    """
    return f"Deleted files at {path}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient.

    This tool requires human approval before execution in this example.
    """
    return f"Email sent to {to} — subject: {subject}"
