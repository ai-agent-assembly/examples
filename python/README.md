# Python Examples

This directory contains runnable Python examples showing how to integrate Agent Assembly with popular AI agent frameworks.

## What lives here

| Sub-project (coming soon)          | Framework        | What it demonstrates                                      |
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

All examples use the `agent-assembly` Python package (available on PyPI).

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
