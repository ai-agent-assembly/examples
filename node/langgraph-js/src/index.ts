import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { END, StateGraph } from "./graph.js";
import { createPolicyGatewayClient } from "./policy.js";
import { TOOLS } from "./tools.js";

interface GraphState {
  query: string;
  log: string[];
}

// region: quickstart
/**
 * Build governed tools once, then call them from inside graph nodes.
 * withAssembly enforces the local policy before each tool runs.
 */
function buildGovernedTools() {
  return withAssembly(
    {
      search_docs: {
        execute: async (args: Record<string, unknown>) => TOOLS.search_docs(args).output,
      },
      execute_shell: {
        execute: async (args: Record<string, unknown>) => TOOLS.execute_shell(args).output,
      },
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "langgraph-js-example-agent" }
  );
}
// endregion

async function main(): Promise<void> {
  console.log("=== LangGraph.js-style Graph — Agent Assembly Governance Example ===\n");
  console.log("A two-node state machine whose tool calls are governed by withAssembly.\n");

  const tools = buildGovernedTools();

  const graph = new StateGraph<GraphState>()
    .addNode("search", async (state) => {
      console.log('Node "search" — calling allowed tool: search_docs');
      const out = await tools.search_docs.execute({ query: state.query });
      console.log(`  [ALLOW] ${out}`);
      return { ...state, log: [...state.log, String(out)] };
    })
    .addNode("escalate", async (state) => {
      console.log('\nNode "escalate" — calling denied tool: execute_shell');
      try {
        await tools.execute_shell.execute({ command: "rm -rf /" });
      } catch (err) {
        if (err instanceof PolicyViolationError) {
          console.log(`  [BLOCKED] ${err.message}`);
          return { ...state, log: [...state.log, `BLOCKED: ${err.message}`] };
        }
        throw err;
      }
      return state;
    })
    .setEntryPoint("search")
    .addEdge("search", "escalate")
    .addEdge("escalate", END)
    .compile();

  const finalState = await graph.invoke({ query: "How does Agent Assembly work?", log: [] });

  console.log(`\nGraph finished with ${finalState.log.length} logged steps.`);
  console.log("Done. Graph-node tool calls governed by withAssembly + the local policy.");
}

try {
  await main();
} catch (err) {
  console.error(err);
  process.exit(1);
}
