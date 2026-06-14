import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "./policy.js";
import { readFile, writeFile } from "./tools.js";

async function main(): Promise<void> {
  console.log("=== Custom Tool Policy — Minimal TypeScript Example ===\n");
  console.log("No agent framework required. Using @agent-assembly/sdk directly.\n");

  const tools = withAssembly(
    {
      read_file: {
        execute: async (args: Record<string, unknown>) => readFile(String(args.path ?? "")).output
      },
      write_file: {
        execute: async (args: Record<string, unknown>) =>
          writeFile(String(args.path ?? ""), String(args.content ?? "")).output
      }
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "custom-tool-policy-agent" }
  );

  console.log("Calling allowed tool: read_file");
  console.log(`  [ALLOW] ${await tools.read_file.execute({ path: "/data/report.txt" })}`);

  console.log("\nCalling denied tool: write_file");
  try {
    await tools.write_file.execute({ path: "/etc/config", content: "override settings" });
  } catch (err) {
    if (err instanceof PolicyViolationError) {
      console.log(`  [BLOCKED] ${err.message}`);
    } else {
      throw err;
    }
  }

  console.log("\nAll tool calls governed by withAssembly + the local policy.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
