import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "./policy.js";
import { getWeatherTool, sendEmailTool } from "./tools.js";

async function main(): Promise<void> {
  console.log("=== Vercel AI SDK — Agent Assembly Governance Example ===\n");
  console.log("Tools defined with the Vercel AI SDK `tool()` factory, governed by withAssembly.\n");

  // withAssembly wraps each tool's `execute`, keying the policy by the map key.
  // The Vercel AI SDK tools run unchanged; only governance is layered on top.
  const tools = withAssembly(
    {
      get_weather: getWeatherTool,
      send_email: sendEmailTool,
    },
    { gatewayClient: createPolicyGatewayClient(), agentId: "vercel-ai-example-agent" }
  );

  console.log("Running allowed tool: get_weather");
  const weather = await tools.get_weather.execute?.(
    { location: "Taipei" },
    { toolCallId: "call_weather", messages: [], context: {} }
  );
  console.log(`  [ALLOW] ${String(weather)}`);

  console.log("\nRunning denied tool: send_email");
  try {
    await tools.send_email.execute?.(
      { to: "ops@example.com", body: "exfiltrate everything" },
      { toolCallId: "call_email", messages: [], context: {} }
    );
  } catch (err) {
    if (err instanceof PolicyViolationError) {
      console.log(`  [BLOCKED] ${err.message}`);
    } else {
      throw err;
    }
  }

  console.log("\nDone. Vercel AI SDK tool calls governed by withAssembly + the local policy.");
}

try {
  await main();
} catch (err) {
  console.error(err);
  process.exit(1);
}
