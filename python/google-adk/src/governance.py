"""Governance wiring for the google-adk-governed-agent example.

Governance is installed through the SDK's **public** Google ADK adapter —
``GoogleADKAdapter.register_hooks`` / ``unregister_hooks`` — the same entrypoint
``init_assembly`` uses to wire ADK governance in a live deployment. The adapter
patches ``google.adk.tools.BaseTool.run_async`` and every concrete tool class
exported from ``google.adk.tools`` that overrides ``run_async``, routing each
invocation through the interceptor's ``check_tool_start`` /
``wait_for_tool_approval`` before the tool body runs.

This keeps the demo fully offline (no Gemini / Vertex AI credentials, no
network) while running the genuine allow / deny / pending governance logic.

SDK gap (AAASM-4839): the public adapter has no entrypoint to govern a *single*
caller-supplied tool class — it only auto-discovers concrete tools exported from
``google.adk.tools``. This demo's ``DemoTool`` is a local subclass defined in the
example, so ``govern_tool_class`` registers it into that public discovery scope
before ``register_hooks`` runs. A production agent instead exposes real
``google.adk.tools`` tools (e.g. ``FunctionTool``), which the adapter governs
with no bridging; a public per-class governance API would remove even this step.
"""
from __future__ import annotations

import importlib
from typing import Any

from agent_assembly.adapters.google_adk import GoogleADKAdapter

_ADK_TOOLS_MODULE = "google.adk.tools"

# One adapter instance per governed class: ``unregister_hooks`` only reverts what
# an adapter's own ``register_hooks`` installed, so the instance must be retained.
_ADAPTERS: dict[type[Any], GoogleADKAdapter] = {}


def govern_tool_class(tool_cls: type[Any], interceptor: Any) -> None:
    """Attach Agent Assembly governance to a concrete ADK tool class.

    Wires the class through the public ``GoogleADKAdapter`` so every
    ``run_async`` invocation is checked against the interceptor
    (``check_tool_start`` / ``wait_for_tool_approval``) before the tool body runs.
    """
    adk_tools = importlib.import_module(_ADK_TOOLS_MODULE)
    # Bridge the local demo tool into the adapter's public discovery scope — see
    # the module docstring's "SDK gap" note for why this is needed here but not
    # for a production agent using real ``google.adk.tools`` tools.
    setattr(adk_tools, tool_cls.__name__, tool_cls)
    adapter = GoogleADKAdapter()
    adapter.register_hooks(interceptor)
    _ADAPTERS[tool_cls] = adapter


def ungovern_tool_class(tool_cls: type[Any]) -> None:
    """Revert governance hooks installed by ``govern_tool_class``."""
    adapter = _ADAPTERS.pop(tool_cls, None)
    if adapter is not None:
        adapter.unregister_hooks()
    adk_tools = importlib.import_module(_ADK_TOOLS_MODULE)
    if getattr(adk_tools, tool_cls.__name__, None) is tool_cls:
        delattr(adk_tools, tool_cls.__name__)
