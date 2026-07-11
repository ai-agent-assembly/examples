"""Real Semantic Kernel functions for the semantic-kernel-tool-policy example.

Each tool is a genuine Semantic Kernel ``@kernel_function`` on a plugin — the
same ``KernelFunction`` a Semantic Kernel ``Kernel`` invokes when the model (or
a planner) selects a tool. Three functions:

  - get_weather    — safe read-only lookup      (ALLOWED by policy)
  - summarize_docs — safe summarisation tool     (ALLOWED by policy)
  - execute_sql    — arbitrary SQL execution     (DENIED by policy)

The ``execute_sql`` body records into ``SQL_EXECUTIONS`` so the demo (and the
smoke test) can prove a denied tool's body never runs — governance short-circuits
it before ``Kernel.invoke`` reaches the function body.

Semantic Kernel is **distinct from the Microsoft Agent Framework** (which has its
own example and a native adapter); this example targets Semantic Kernel's
``KernelFunction`` execution path, which has no native adapter.
"""

from __future__ import annotations

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

#: Plugin name the tools are registered under on the kernel.
PLUGIN_NAME = "tools"

#: Side-effect sink: ``execute_sql`` appends here when its body actually runs.
#: A governed deny must leave this empty — proof the body was short-circuited.
SQL_EXECUTIONS: list[str] = []


class ToolsPlugin:
    """A Semantic Kernel plugin of native (code) functions — no LLM required."""

    @kernel_function(name="get_weather", description="Get the current weather for a city.")
    def get_weather(self, city: str) -> str:
        return f"Weather in {city}: sunny, 22C (mock)"

    @kernel_function(
        name="summarize_docs", description="Summarize documents related to a topic."
    )
    def summarize_docs(self, topic: str) -> str:
        return f"Summary for '{topic}': Agent Assembly provides governance... (mock)"

    @kernel_function(
        name="execute_sql",
        description="Execute an arbitrary SQL statement against the database (DANGEROUS).",
    )
    def execute_sql(self, sql: str) -> str:
        # DANGEROUS: blocked by policy. If governance works, this never runs for
        # a denied call, so SQL_EXECUTIONS stays empty.
        SQL_EXECUTIONS.append(sql)
        return f"SQL result for: {sql}"


def build_kernel() -> Kernel:
    """Return a Kernel with the demo tools registered under ``PLUGIN_NAME``."""
    kernel = Kernel()
    kernel.add_plugin(ToolsPlugin(), plugin_name=PLUGIN_NAME)
    return kernel
