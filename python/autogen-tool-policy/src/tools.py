"""Real AutoGen (autogen-core) function tools for the autogen-tool-policy example.

Each tool is a genuine ``autogen_core.tools.FunctionTool`` — the same object an
AutoGen ``AssistantAgent`` invokes when the model chooses a tool. Three tools:

  - get_weather    — safe read-only lookup      (ALLOWED by policy)
  - summarize_docs — safe summarisation tool     (ALLOWED by policy)
  - execute_sql    — arbitrary SQL execution     (DENIED by policy)

The ``execute_sql`` body records into ``SQL_EXECUTIONS`` so the demo (and the
smoke test) can prove a denied tool's body never runs — governance short-circuits
it before ``FunctionTool.run_json`` reaches the function body.
"""

from __future__ import annotations

from autogen_core.tools import FunctionTool

#: Side-effect sink: ``execute_sql`` appends here when its body actually runs.
#: A governed deny must leave this empty — proof the body was short-circuited.
SQL_EXECUTIONS: list[str] = []


def _get_weather(city: str) -> str:
    return f"Weather in {city}: sunny, 22C (mock)"


def _summarize_docs(topic: str) -> str:
    return f"Summary for '{topic}': Agent Assembly provides governance... (mock)"


def _execute_sql(sql: str) -> str:
    # DANGEROUS: blocked by policy. If governance works, this never runs for a
    # denied call, so SQL_EXECUTIONS stays empty.
    SQL_EXECUTIONS.append(sql)
    return f"SQL result for: {sql}"


get_weather = FunctionTool(
    _get_weather, name="get_weather", description="Get the current weather for a city."
)
summarize_docs = FunctionTool(
    _summarize_docs,
    name="summarize_docs",
    description="Summarize documents related to a topic.",
)
execute_sql = FunctionTool(
    _execute_sql,
    name="execute_sql",
    description="Execute an arbitrary SQL statement against the database (DANGEROUS).",
)
