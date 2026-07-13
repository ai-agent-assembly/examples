import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "./policy.js";
import { TOOLS } from "./tools.js";

async function main(): Promise<void> {
  console.log("=== LangChain.js-style Agent Assembly Example ===\n");

  // region: quickstart
  const tools = withAssembly(
    {
      get_weather: {
        execute: async (args: Record<string, unknown>) => TOOLS.get_weather(args).output
      },
      delete_file: {
        execute: async (args: Record<string, unknown>) => TOOLS.delete_file(args).output
      }
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "langchain-js-example-agent" }
  );
  // endregion

  console.log("Running allowed tool: get_weather");
  console.log(`  [ALLOW] ${await tools.get_weather.execute({ location: "Taipei" })}`);

  console.log("\nRunning denied tool: delete_file");
  try {
    await tools.delete_file.execute({ path: "/etc/hosts" });
  } catch (err) {
    if (err instanceof PolicyViolationError) {
      console.log(`  [BLOCKED] ${err.message}`);
    } else {
      throw err;
    }
  }

  console.log("\nDone. Tool calls governed by withAssembly + the local policy.");
}

try {
  await main();
} catch (err) {
  console.error(err);
  process.exit(1);
}
