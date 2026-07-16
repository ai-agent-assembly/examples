# Python Examples

This directory contains runnable Python examples showing how to integrate Agent Assembly with popular AI agent frameworks.

## What lives here

| Sub-project                        | Framework        | What it demonstrates                                      |
|------------------------------------|------------------|-----------------------------------------------------------|
| `langchain-basic-agent/`           | LangChain        | Wire Agent Assembly SDK into a basic LangChain agent      |
| `openai-agents-sdk/`               | OpenAI Agents SDK| Govern tool calls made by an OpenAI Agents SDK agent      |
| `llamaindex-tool-policy/`          | LlamaIndex       | Enforce tool-level allow/deny policies with LlamaIndex    |
| `custom-tool-policy/`              | —                | Write a custom Python tool wrapper with SDK               |
| `langchain-research-agent/`        | LangChain        | ReAct research agent with budget, egress allowlist, and credential-leak blocking |
| `crewai-research-crew/`            | CrewAI           | Multi-agent crew with delegation tracking, file-write approval, and shared budget |
| `langgraph/`                       | LangGraph        | Node-level governance on a compiled `StateGraph`, blocking a destructive tool mid-graph |
| `pydantic-ai/`                     | Pydantic AI      | Tool-call governance driven offline by `TestModel` (allow / deny / pending) |
| `google-adk/`                      | Google ADK       | Scripted offline tool trajectory governing `BaseTool.run_async` (no cloud creds) |
| `haystack-tool-policy/`            | Haystack         | Govern a real Haystack agent via the native adapter — real `Tool.invoke` allow/deny through a `ToolInvoker` |
| `smolagents-tool-policy/`          | Smolagents       | Govern real `smolagents.Tool` calls via `Tool.__call__`, blocking a destructive tool offline (no model creds) |
| `microsoft-agent-framework-tool-policy/` | Microsoft Agent Framework | Govern `FunctionTool.invoke` (allow / deny / pending); mock + live paths |
| `agno-tool-policy/`                | Agno             | Govern real Agno `FunctionCall.execute` tool calls (allow / deny / pending); offline, no model creds |
| `autogen-tool-policy/`             | AutoGen / ag2    | Govern real `autogen_core.tools.FunctionTool.run_json` calls, blocking a destructive tool offline (no model creds) |
| `semantic-kernel-tool-policy/`     | Semantic Kernel  | Govern real Semantic Kernel `Kernel.invoke` calls, blocking a destructive tool offline (no model creds) |
| `strands-agents-tool-policy/`      | Strands Agents   | Govern real `@strands.tool` invocations, blocking a destructive tool offline (no model creds) |

All examples use the `agent-assembly` Python package (available on PyPI).

## Framework coverage goal

**Decision (AAASM-4458):** this repo **adopts an explicit framework-coverage matrix** —
the table below — instead of relying only on the descriptive catalog above. The
catalog grows organically and makes gaps invisible; a stated matrix makes any
missing framework visible by inspection, so the next gap surfaces without another
ad-hoc audit. When a new framework gains an example, move it to **Have example**;
when the team commits to one, add it under **Planned**; frameworks intentionally
out of scope go under **Not planned** with a one-line reason.

| Framework | Status | Notes |
|---|---|---|
| LangChain | Have example | `langchain-basic-agent`, `langchain-research-agent` |
| LangGraph | Have example | `langgraph` |
| CrewAI | Have example | `crewai-research-crew` |
| OpenAI Agents SDK | Have example | `openai-agents-sdk` |
| Pydantic AI | Have example | `pydantic-ai` |
| Google ADK | Have example | `google-adk` |
| LlamaIndex | Have example | `llamaindex-tool-policy` |
| Haystack | Have example | `haystack-tool-policy` |
| Smolagents (Hugging Face) | Have example | `smolagents-tool-policy` |
| Microsoft Agent Framework | Have example | `microsoft-agent-framework-tool-policy` (distinct from Semantic Kernel) |
| Agno | Have example | `agno-tool-policy` |
| AutoGen / ag2 | Have example | `autogen-tool-policy` |
| Microsoft Semantic Kernel | Have example | `semantic-kernel-tool-policy` (distinct from the Agent Framework) |
| Strands Agents (AWS) | Have example | `strands-agents-tool-policy` |
| Framework-agnostic (plain Python) | Have example | `custom-tool-policy` |
| _(next candidate)_ | Not planned yet | Open a ticket to move a framework to **Planned** before adding an example |

## Prerequisites

- Python >= 3.12
- `uv` (recommended) or `pip`
- A running Agent Assembly gateway (see the sub-project README for local dev options)

## Expected sub-project structure

Each sub-project in this directory should follow this layout:

```text
python/<example-name>/
  README.md         ← prerequisites, setup, run, expected output, troubleshooting
  .env.example      ← template for any required secrets or config (never .env)
  pyproject.toml    ← or requirements.txt
  src/
    main.py         ← entrypoint
```

## Back to root

[← Agent Assembly Examples](../README.md)
