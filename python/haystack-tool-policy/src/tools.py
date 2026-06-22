"""Real Haystack ``Tool`` definitions for the haystack-tool-policy example.

Three genuine ``haystack.tools.Tool`` instances:
  - query_index     — safe read-only retrieval (ALLOWED by policy)
  - summarize_docs  — safe summarisation tool (ALLOWED by policy)
  - execute_sql     — arbitrary SQL execution (DENIED by policy)

Each tool's underlying function records that it ran, so the demo (and the smoke
tests) can prove a denied tool's body never executes — governance, not a no-op.
"""

from __future__ import annotations

from haystack.tools import Tool

#: Records which tool functions actually executed, so a deny is observable as
#: "the body never ran" rather than just "a blocked message came back".
EXECUTED: list[str] = []


def _query_index_fn(query: str) -> str:
    EXECUTED.append("query_index")
    return f"Index results for '{query}': [chunk-12, chunk-44, chunk-07] (mock)"


def _summarize_docs_fn(topic: str) -> str:
    EXECUTED.append("summarize_docs")
    return f"Summary for '{topic}': Agent Assembly provides governance... (mock)"


def _execute_sql_fn(sql: str) -> str:
    EXECUTED.append("execute_sql")
    return f"SQL result for: {sql}"


def build_tools() -> list[Tool]:
    """Return the three real Haystack tools the demo governs."""
    return [
        Tool(
            name="query_index",
            description="Query the document index for relevant information.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            function=_query_index_fn,
        ),
        Tool(
            name="summarize_docs",
            description="Summarize documents related to a topic.",
            parameters={
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
            function=_summarize_docs_fn,
        ),
        Tool(
            name="execute_sql",
            description="Execute an arbitrary SQL statement against the database.",
            parameters={
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
            function=_execute_sql_fn,
        ),
    ]
