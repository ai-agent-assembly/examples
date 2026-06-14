import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "./policy.js";
import { getStockPriceTool, placeTradeTool } from "./tools.js";

/**
 * Run a Mastra tool's `execute`. Mastra's signature is `(inputData, context) => ...`;
 * the tools here ignore the context, so an empty object is sufficient for the demo.
 */
async function runMastraTool(
  tool: { execute?: ((inputData: never, context: never) => Promise<unknown>) | undefined },
  input: Record<string, unknown>
): Promise<unknown> {
  if (!tool.execute) {
    throw new Error("tool has no execute function");
  }
  return tool.execute(input as never, {} as never);
}

async function main(): Promise<void> {
  console.log("=== Mastra — Agent Assembly Governance Example ===\n");
  console.log("Tools defined with Mastra's createTool, governed by withAssembly.\n");

  // Wrap the Mastra tools with withAssembly. Each governed entry delegates to the
  // real Mastra tool's execute, so the policy is enforced before the tool runs.
  const tools = withAssembly(
    {
      get_stock_price: {
        execute: async (args: Record<string, unknown>) => runMastraTool(getStockPriceTool, args),
      },
      place_trade: {
        execute: async (args: Record<string, unknown>) => runMastraTool(placeTradeTool, args),
      },
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "mastra-example-agent" }
  );

  console.log("Running allowed tool: get_stock_price");
  const price = await tools.get_stock_price.execute({ ticker: "AASM" });
  console.log(`  [ALLOW] ${JSON.stringify(price)}`);

  console.log("\nRunning denied tool: place_trade");
  try {
    await tools.place_trade.execute({ ticker: "AASM", shares: 100 });
  } catch (err) {
    if (err instanceof PolicyViolationError) {
      console.log(`  [BLOCKED] ${err.message}`);
    } else {
      throw err;
    }
  }

  console.log("\nDone. Mastra tool calls governed by withAssembly + the local policy.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
