import { initAssembly, withAssembly } from "@agent-assembly/sdk";
import { evaluate } from "./policy.js";
import { TOOL_DEFINITIONS, searchWeb, sendEmail } from "./tools.js";

async function dispatchToolCall(name: string, args: Record<string, unknown>): Promise<string> {
  const rule = evaluate(name);
  if (rule.action === "deny") {
    const msg = `[POLICY DENY] ${name}: ${rule.reason}`;
    console.log(msg);
    return msg;
  }
  if (name === "search_web") {
    const result = searchWeb(String(args["query"] ?? ""));
    console.log(`[POLICY ALLOW] ${name}: ${result.output}`);
    return result.output;
  }
  if (name === "send_email") {
    const result = sendEmail(String(args["to"] ?? ""), String(args["subject"] ?? ""));
    console.log(result.output);
    return result.output;
  }
  return `[ERROR] Unknown tool: ${name}`;
}

async function main(): Promise<void> {
  console.log("=== OpenAI Node SDK-style Agent Assembly Example ===\n");
  console.log("Available tools:", TOOL_DEFINITIONS.map((t) => t.function.name).join(", "));
  console.log();

  const _ctx = await initAssembly({
    agentId: "openai-node-example-agent",
    mode: "auto",
  });

  const wrappedDispatch = withAssembly(dispatchToolCall, {
    agentId: "openai-node-example-agent",
  });

  console.log("Simulating OpenAI tool call: search_web");
  await wrappedDispatch("search_web", { query: "Agent Assembly governance" });

  console.log("\nSimulating OpenAI tool call: send_email (should be denied)");
  await wrappedDispatch("send_email", {
    to: "user@example.com",
    subject: "Hello from agent",
    body: "This would require approval.",
  });

  console.log("\nAudit events emitted to gateway (or noop in offline mode).");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
