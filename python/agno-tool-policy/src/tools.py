"""Agno function-tool definitions for the agno-tool-policy example.

Each tool is a real Agno ``@tool`` (an ``agno.tools.function.Function``), the same
object an Agno ``Agent`` invokes when the model chooses a tool. Three tools:

  - get_weather    — safe read-only lookup        (ALLOWED by policy)
  - summarize_docs — safe summarisation tool       (ALLOWED by policy)
  - execute_sql    — arbitrary SQL execution       (DENIED by policy)

The ``execute_sql`` body records into ``SQL_EXECUTIONS`` so the demo (and the
smoke test) can prove a denied tool's body never runs — governance short-circuits
it before execution.
"""

from __future__ import annotations

from agno.tools import tool

#: Side-effect sink: ``execute_sql`` appends here when its body actually runs.
#: A governed deny must leave this empty — proof the body was short-circuited.
SQL_EXECUTIONS: list[str] = []


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Weather in {city}: sunny, 22C (mock)"


@tool
def summarize_docs(topic: str) -> str:
    """Summarize documents related to a topic."""
    return f"Summary for '{topic}': Agent Assembly provides governance... (mock)"


@tool
def execute_sql(sql: str) -> str:
    """Execute an arbitrary SQL statement against the database.

    This tool is DANGEROUS and is blocked by policy in this example. If
    governance is working, this body never runs for a denied call.
    """
    SQL_EXECUTIONS.append(sql)
    return f"SQL result for: {sql}"
