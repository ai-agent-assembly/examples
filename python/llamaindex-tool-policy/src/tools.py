"""LlamaIndex FunctionTool definitions for the llamaindex-tool-policy example.

Three tools are defined:
  - query_index     — safe read-only retrieval (ALLOWED by policy)
  - summarize_docs  — safe summarisation tool (ALLOWED by policy)
  - execute_sql     — arbitrary SQL execution (DENIED by policy)
"""
from __future__ import annotations

from llama_index.core.tools import FunctionTool


def _query_index_fn(query: str) -> str:
    """Query the document index for relevant information."""
    return f"📚 Index results for '{query}': [chunk-12, chunk-44, chunk-07] (mock)"


def _summarize_docs_fn(topic: str) -> str:
    """Summarize documents related to a topic."""
    return f"📝 Summary for '{topic}': Agent Assembly provides governance... (mock)"


def _execute_sql_fn(sql: str) -> str:
    """Execute an arbitrary SQL statement against the database.

    This tool is DANGEROUS and is blocked by policy in this example.
    """
    return f"SQL result for: {sql}"


query_index = FunctionTool.from_defaults(
    fn=_query_index_fn,
    name="query_index",
    description="Query the document index for relevant information.",
)

summarize_docs = FunctionTool.from_defaults(
    fn=_summarize_docs_fn,
    name="summarize_docs",
    description="Summarize documents related to a topic.",
)

execute_sql = FunctionTool.from_defaults(
    fn=_execute_sql_fn,
    name="execute_sql",
    description="Execute an arbitrary SQL statement against the database.",
)
