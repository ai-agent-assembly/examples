"""Real ``smolagents.Tool`` definitions for the smolagents-tool-policy example.

These are genuine smolagents tools (subclasses of ``smolagents.Tool``), the same
kind a ``ToolCallingAgent`` or ``CodeAgent`` would call. The governance adapter
wraps ``Tool.__call__`` so these tools are governed without any change to the
tool code itself — exactly how the SDK governs a real agent's tools.

  - ``search_docs``        — safe read-only retrieval (ALLOWED by policy)
  - ``summarize``          — safe summarisation tool (ALLOWED by policy)
  - ``run_shell_command``  — arbitrary command execution (DENIED by policy)
"""

from __future__ import annotations

from smolagents import Tool


class SearchDocsTool(Tool):  # type: ignore[misc]  # base is a runtime framework class (untyped)
    name = "search_docs"
    description = "Search the documentation index for a query."
    inputs = {"query": {"type": "string", "description": "the search query"}}
    output_type = "string"

    def forward(self, query: str) -> str:
        return f"docs results for '{query}': [chunk-12, chunk-44, chunk-07] (mock)"


class SummarizeTool(Tool):  # type: ignore[misc]  # base is a runtime framework class (untyped)
    name = "summarize"
    description = "Summarize documents related to a topic."
    inputs = {"topic": {"type": "string", "description": "the topic to summarize"}}
    output_type = "string"

    def forward(self, topic: str) -> str:
        return (
            f"summary of '{topic}': Agent Assembly governs agent tool calls... (mock)"
        )


class RunShellCommandTool(Tool):  # type: ignore[misc]  # base is a runtime framework class (untyped)
    name = "run_shell_command"
    description = "Execute an arbitrary shell command on the host."

    inputs = {"command": {"type": "string", "description": "the shell command to run"}}
    output_type = "string"

    def forward(self, command: str) -> str:
        # In a real deployment this would actually run the command — which is
        # precisely why the policy denies it before forward() ever executes.
        return f"executed shell command: {command}"


def build_tools() -> dict[str, Tool]:
    """Construct the demo's real smolagents tools, keyed by tool name."""
    tools: list[Tool] = [SearchDocsTool(), SummarizeTool(), RunShellCommandTool()]
    return {tool.name: tool for tool in tools}
