# Choosing an Example

Use this guide to find the right starting point in this repository based on your language, framework, and what you want to learn.

## Step 1 — What is your primary language?

```
Which language are you using?
├── Python  → go to Step 2 (Python)
├── Node.js / TypeScript  → go to Step 3 (Node.js)
├── Go  → go to Step 4 (Go)
└── I want a cross-language scenario  → go to Step 5 (Scenarios)
```

---

## Step 2 — Python examples

> See [`python/README.md`](../python/README.md) for the full index.

| I want to…                                     | Example sub-project                            |
|------------------------------------------------|------------------------------------------------|
| Wire Agent Assembly into a LangChain agent     | `python/langchain-basic-agent/`               |
| Run a LangChain ReAct research agent           | `python/langchain-research-agent/`            |
| Use the OpenAI Agents SDK                      | `python/openai-agents-sdk/`                   |
| Apply tool-level policies with LlamaIndex      | `python/llamaindex-tool-policy/`              |
| Write a custom tool wrapper with SDK           | `python/custom-tool-policy/`                  |
| Govern nodes of a LangGraph `StateGraph`       | `python/langgraph/`                           |
| Govern Pydantic AI tool calls (offline `TestModel`) | `python/pydantic-ai/`                    |
| Govern a Google ADK agent (scripted, no live LLM)¹ | `python/google-adk/`                      |
| Govern a CrewAI multi-agent research crew      | `python/crewai-research-crew/`                |
| Govern an AutoGen (`autogen-core`) agent       | `python/autogen-tool-policy/`                 |
| Apply tool policies with the native Agno adapter | `python/agno-tool-policy/`                  |
| Govern a Haystack agent via the native adapter | `python/haystack-tool-policy/`                |
| Govern Microsoft Agent Framework tool calls    | `python/microsoft-agent-framework-tool-policy/` |
| Govern Microsoft Semantic Kernel tool calls    | `python/semantic-kernel-tool-policy/`         |
| Govern Smolagents (Hugging Face) tool calls    | `python/smolagents-tool-policy/`              |
| Govern Strands Agents (AWS) tool calls         | `python/strands-agents-tool-policy/`          |

¹ The `google-adk` example replays a **scripted tool trajectory** with no live
LLM — Google ADK normally drives its loop against a cloud model (Gemini /
Vertex AI), so the example invokes real `BaseTool.run_async` directly to keep CI
offline and credential-free. The allow / deny / pending governance path is real.

All Python examples use the `agent-assembly` Python SDK (PyPI package).

---

## Step 3 — Node.js / TypeScript examples

> See [`node/README.md`](../node/README.md) for the full index.

| I want to…                                     | Example sub-project (coming soon)              |
|------------------------------------------------|------------------------------------------------|
| Wire Agent Assembly into a LangChain.js agent  | `node/langchain-js-basic-agent/`              |
| Apply tool policies with the OpenAI Node SDK   | `node/openai-node-tool-policy/`               |
| Write a custom TypeScript tool wrapper         | `node/custom-tool-policy/`                    |
| Govern Vercel AI SDK `tool()` calls            | `node/vercel-ai/`                             |
| Govern tool calls in a LangGraph.js state machine² | `node/langgraph-js/`                      |
| Govern Mastra `createTool` calls               | `node/mastra/`                                |

² The `langgraph-js` example uses a **hand-rolled `StateGraph`**, not the real
`@langchain/langgraph` (which transitively pulls `@langchain/core`). It replays
the LangGraph.js graph shape so the example stays offline and dependency-free in
CI; the `withAssembly` governance path is identical to a real graph.

All Node.js examples use the `@agent-assembly/sdk` npm package.

---

## Step 4 — Go examples

> See [`go/README.md`](../go/README.md) for the full index.

| I want to…                                     | Example sub-project (coming soon)              |
|------------------------------------------------|------------------------------------------------|
| Build a basic governed agent in Go             | `go/basic-agent/`                             |
| Enforce tool-level policies in Go              | `go/tool-policy/`                             |
| Govern a LangChainGo agent's tool calls        | `go/langchaingo/`                             |
| Integrate the Agent Assembly CLI runtime       | `go/cli-runtime-integration/`                 |

All Go examples use the `github.com/ai-agent-assembly/go-sdk` module.

---

## Step 5 — Cross-language scenarios

> See [`scenarios/README.md`](../scenarios/README.md) for the full index.

These examples demonstrate a specific Agent Assembly capability in a language-agnostic way. Pick by what you want to understand.

| I want to understand…                          | Scenario sub-project (coming soon)             |
|------------------------------------------------|------------------------------------------------|
| How policy enforcement works end-to-end        | `scenarios/policy-enforcement/`               |
| How human-in-the-loop approval gates work      | `scenarios/approval-gates/`                   |
| How audit trail and trace are captured         | `scenarios/audit-trace/`                      |
| How budget limits stop runaway spend           | `scenarios/budget-limits/`                    |
| How the sidecar proxy intercepts without SDK   | `scenarios/sidecar-runtime/`                  |
| How the real SDK is governed end-to-end by a live core³ | `scenarios/live-core-enforcement/`   |

³ Unlike the other scenarios (which ship an offline SDK-shaped stand-in),
`live-core-enforcement` imports the **real** `agent_assembly` SDK and runs it
against a real `aa-runtime` + `aa-gateway` over Docker — a policy `deny` actually
blocks the tool. It is Python-only and requires Docker (and a published gateway
image); see its README.

---

## Still not sure?

If you are completely new to Agent Assembly, the recommended path is:

1. Read [concepts.md](./concepts.md) to understand the three interception layers.
2. Pick a **Python** or **Node.js** SDK example that matches your framework.
3. Get it running locally with mock provider credentials.
4. Then explore a **scenario** example to see policy enforcement, approval gates, or audit tracing in action.
