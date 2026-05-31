"""OpenAI Agents SDK tool definitions for the openai-agents-sdk example.

Three tools are defined as plain Python functions. When registered as
OpenAI FunctionTools, Agent Assembly intercepts their execution and
applies governance policy before the function body runs.

  - search_documents    — safe read-only tool (ALLOWED by policy)
  - send_message_to_user — outbound action tool (requires APPROVAL)
  - delete_record       — destructive data tool (DENIED by policy)
"""
from __future__ import annotations


def search_documents(query: str) -> str:
    """Search the internal knowledge base for the given query.

    Returns mock results in offline / demo mode.
    """
    return f"📄 Search results for '{query}': [doc-42, doc-17, doc-99] (mock)"


def send_message_to_user(user_id: str, message: str) -> str:
    """Send a message to a user.

    This tool requires human approval before execution in this example.
    """
    return f"Message sent to user {user_id}: {message}"


def delete_record(record_id: str) -> str:
    """Permanently delete a database record.

    This tool is DANGEROUS and is blocked by policy in this example.
    """
    return f"Record {record_id} deleted."
