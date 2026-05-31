import { initAssembly, withAssembly } from "@agent-assembly/sdk";
import { evaluate } from "./policy.js";
import { readFile, writeFile } from "./tools.js";

async function executeTool(
  name: string,
  args: Record<string, unknown>,
): Promise<string> {
  const rule = evaluate(name);
  if (rule.action === "deny") {
    const msg = `[POLICY DENY] ${name}: ${rule.reason}`;
    console.log(msg);
    return msg;
  }
  if (name === "read_file") {
    const result = readFile(String(args["path"] ?? ""));
    console.log(`[POLICY ALLOW] ${name}: ${result.output}`);
    return result.output;
  }
  if (name === "write_file") {
    const result = writeFile(String(args["path"] ?? ""), String(args["content"] ?? ""));
    console.log(result.output);
    return result.output;
  }
  return `[ERROR] Unknown tool: ${name}`;
}

async function main(): Promise<void> {
  console.log("=== Custom Tool Policy — Minimal TypeScript Example ===\n");
  console.log("No agent framework required. Using @agent-assembly/sdk directly.\n");

  const _ctx = await initAssembly({
    agentId: "custom-tool-policy-agent",
    mode: "auto",
  });

  const govern = withAssembly(executeTool, { agentId: "custom-tool-policy-agent" });

  console.log("Calling allowed tool: read_file");
  await govern("read_file", { path: "/data/report.txt" });

  console.log("\nCalling denied tool: write_file");
  await govern("write_file", { path: "/etc/config", content: "override settings" });

  console.log("\nAll tool calls governed by policy. Audit emitted to gateway (or noop).");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
