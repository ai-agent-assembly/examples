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

| I want to…                                     | Example sub-project (coming soon)              |
|------------------------------------------------|------------------------------------------------|
| Wire Agent Assembly into a LangChain agent     | `python/langchain-basic-agent/`               |
| Use the OpenAI Agents SDK                      | `python/openai-agents-sdk/`                   |
| Apply tool-level policies with LlamaIndex      | `python/llamaindex-tool-policy/`              |
| Write a custom tool wrapper with SDK           | `python/custom-tool-policy/`                  |

All Python examples use the `agent-assembly` Python SDK (PyPI package).

---

## Step 3 — Node.js / TypeScript examples

> See [`node/README.md`](../node/README.md) for the full index.

| I want to…                                     | Example sub-project (coming soon)              |
|------------------------------------------------|------------------------------------------------|
| Wire Agent Assembly into a LangChain.js agent  | `node/langchain-js-basic-agent/`              |
| Apply tool policies with the OpenAI Node SDK   | `node/openai-node-tool-policy/`               |
| Write a custom TypeScript tool wrapper         | `node/custom-tool-policy/`                    |

All Node.js examples use the `@agent-assembly/sdk` npm package.

---

## Step 4 — Go examples

> See [`go/README.md`](../go/README.md) for the full index.

| I want to…                                     | Example sub-project (coming soon)              |
|------------------------------------------------|------------------------------------------------|
| Build a basic governed agent in Go             | `go/basic-agent/`                             |
| Enforce tool-level policies in Go              | `go/tool-policy/`                             |
| Integrate the Agent Assembly CLI runtime       | `go/cli-runtime-integration/`                 |

All Go examples use the `github.com/agent-assembly/go-sdk` module.

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

---

## Still not sure?

If you are completely new to Agent Assembly, the recommended path is:

1. Read [concepts.md](./concepts.md) to understand the three interception layers.
2. Pick a **Python** or **Node.js** SDK example that matches your framework.
3. Get it running locally with mock provider credentials.
4. Then explore a **scenario** example to see policy enforcement, approval gates, or audit tracing in action.
