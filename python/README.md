# Python Examples

This directory contains runnable Python examples showing how to integrate Agent Assembly with popular AI agent frameworks.

## What lives here

| Sub-project (coming soon)          | Framework        | What it demonstrates                                      |
|------------------------------------|------------------|-----------------------------------------------------------|
| `langchain-basic-agent/`           | LangChain        | Wire Agent Assembly SDK into a basic LangChain agent      |
| `openai-agents-sdk/`               | OpenAI Agents SDK| Govern tool calls made by an OpenAI Agents SDK agent      |
| `llamaindex-tool-policy/`          | LlamaIndex       | Enforce tool-level allow/deny policies with LlamaIndex    |
| `custom-tool-policy/`              | —                | Write a custom Python tool wrapper with SDK               |

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
