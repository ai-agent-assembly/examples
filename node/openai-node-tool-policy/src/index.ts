import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "./policy.js";
import { TOOL_DEFINITIONS, searchWeb, sendEmail } from "./tools.js";

async function main(): Promise<void> {
  console.log("=== OpenAI Node SDK-style Agent Assembly Example ===\n");
  console.log("Available tools:", TOOL_DEFINITIONS.map((t) => t.function.name).join(", "));
  console.log();

  // region: quickstart
  const tools = withAssembly(
    {
      search_web: {
        execute: async (args: Record<string, unknown>) =>
          searchWeb(typeof args.query === "string" ? args.query : "").output
      },
      send_email: {
        execute: async (args: Record<string, unknown>) =>
          sendEmail(
            typeof args.to === "string" ? args.to : "",
            typeof args.subject === "string" ? args.subject : ""
          ).output
      }
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "openai-node-example-agent" }
  );
  // endregion

  console.log("Simulating OpenAI tool call: search_web");
  console.log(`  [ALLOW] ${await tools.search_web.execute({ query: "Agent Assembly governance" })}`);

  console.log("\nSimulating OpenAI tool call: send_email (should be denied)");
  try {
    await tools.send_email.execute({ to: "user@example.com", subject: "Hello from agent" });
  } catch (err) {
    if (err instanceof PolicyViolationError) {
      console.log(`  [BLOCKED] ${err.message}`);
    } else {
      throw err;
    }
  }

  console.log("\nTool calls governed by withAssembly + the local policy.");
}

try {
  await main();
} catch (err) {
  console.error(err);
  process.exit(1);
}
