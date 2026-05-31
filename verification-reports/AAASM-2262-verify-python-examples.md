# Verification Report: AAASM-2193 Python Examples

**Ticket**: AAASM-2262  
**Story**: AAASM-2193 — Add Python framework examples to agent-assembly-examples  
**Verified on**: 2026-05-30  
**Repo**: https://github.com/AI-agent-assembly/agent-assembly-examples

---

## Acceptance Criteria Checklist

### ✅ `python/README.md` routes Python developers to each example

File: `python/README.md`  
Contains a routing table with all four sub-projects:
- `langchain-basic-agent/` — LangChain
- `openai-agents-sdk/` — OpenAI Agents SDK
- `llamaindex-tool-policy/` — LlamaIndex
- `custom-tool-policy/` — (no framework)

All links point to the correct sub-directories. **PASS**

---

### ✅ At least four Python sub-projects exist

| Sub-project | Path | Exists |
|---|---|---|
| `langchain-basic-agent` | `python/langchain-basic-agent/` | ✅ |
| `openai-agents-sdk` | `python/openai-agents-sdk/` | ✅ |
| `llamaindex-tool-policy` | `python/llamaindex-tool-policy/` | ✅ |
| `custom-tool-policy` | `python/custom-tool-policy/` | ✅ |

**PASS**

---

### ✅ Each example has a README with install instructions, run command, and expected output

| Sub-project | README | Install cmd | Run cmd | Expected output |
|---|---|---|---|---|
| `langchain-basic-agent` | ✅ | `uv sync --extra dev` | `uv run python src/main.py` | ✅ |
| `openai-agents-sdk` | ✅ | `uv sync --extra dev` | `uv run python src/main.py` | ✅ |
| `llamaindex-tool-policy` | ✅ | `uv sync --extra dev` | `uv run python src/main.py` | ✅ |
| `custom-tool-policy` | ✅ | `uv sync --extra dev` | `uv run python src/main.py` | ✅ |

**PASS**

---

### ✅ Each example includes a smoke test runnable in CI without real API keys

All tests verified locally:

```
python/langchain-basic-agent  — 6 passed
python/openai-agents-sdk      — 7 passed
python/llamaindex-tool-policy — 7 passed
python/custom-tool-policy     — 7 passed
```

Total: **27 tests, 27 passed, 0 failed**

CI workflow `.github/workflows/verify-python.yml` covers all four sub-projects with separate jobs. No API keys or gateway required. **PASS**

---

### ✅ Examples use the public `agent_assembly` Python SDK import path

All examples import from:
- `from agent_assembly import init_assembly`
- `from agent_assembly.adapters.langchain import AssemblyCallbackHandler`
- `from agent_assembly.exceptions import ToolExecutionBlockedError`

Package name in `pyproject.toml`: `agent-assembly>=0.0.1a2` (matches PyPI). **PASS**

---

### ✅ Mock/offline mode is the default for all examples

| Sub-project | Mode | API key needed |
|---|---|---|
| `langchain-basic-agent` | `sdk-only`, `LocalPolicyEngine` | ❌ |
| `openai-agents-sdk` | `sdk-only`, `LocalPolicyEngine` | ❌ |
| `llamaindex-tool-policy` | `sdk-only`, `LocalPolicyEngine` | ❌ |
| `custom-tool-policy` | `sdk-only`, `LocalPolicyEngine` | ❌ |

All `main.py` scripts run fully offline. **PASS**

---

### ✅ No secrets are committed

Verified:
- No `.env` files present in any sub-project directory
- Only `.env.example` files are committed (3 sub-projects; `custom-tool-policy` needs none)
- `.gitignore` covers `.env` files at repo root
- `git grep -r "OPENAI_API_KEY=" .` returns only `.env.example` files

**PASS**

---

### ✅ Root README links to the Python examples section

`README.md` (root) contains links to `python/` sub-projects via the routing table established in AAASM-2192. **PASS**

---

## Summary

All 8 acceptance criteria for AAASM-2193 are satisfied.

| # | Criterion | Result |
|---|---|---|
| 1 | `python/README.md` routes to each example | ✅ PASS |
| 2 | Four Python sub-projects exist | ✅ PASS |
| 3 | Each has README + install + run + expected output | ✅ PASS |
| 4 | Each smoke test passes offline in CI | ✅ PASS |
| 5 | Public `agent_assembly` SDK import path used | ✅ PASS |
| 6 | Mock/offline mode is default | ✅ PASS |
| 7 | No secrets committed | ✅ PASS |
| 8 | Root README links to Python examples | ✅ PASS |

**Verification: COMPLETE. Story AAASM-2193 meets all acceptance criteria.**
