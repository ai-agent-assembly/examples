import { evaluate, POLICY_RULES, DEFAULT_ACTION } from "./policy.js";
import { readConfig, listAgents, deleteAgent, sendEmail } from "./tools.js";

// `tool` is the snake_case policy key (matches policy.yaml / POLICY_RULES and the
// Python twin); `name` is the camelCase TypeScript function dispatched locally.
type DemoCall =
  | { tool: "read_config"; name: "readConfig"; args: { key: string } }
  | { tool: "list_agents"; name: "listAgents"; args: Record<string, never> }
  | { tool: "delete_agent"; name: "deleteAgent"; args: { agentId: string } }
  | { tool: "send_email"; name: "sendEmail"; args: { to: string; subject: string; body: string } };

const DEMO_CALLS: DemoCall[] = [
  { tool: "read_config", name: "readConfig", args: { key: "database.host" } },
  { tool: "list_agents", name: "listAgents", args: {} },
  { tool: "delete_agent", name: "deleteAgent", args: { agentId: "agent-001" } },
  { tool: "send_email", name: "sendEmail", args: { to: "admin@example.com", subject: "Hello", body: "Test message" } },
];

function runTool(call: DemoCall): string {
  switch (call.name) {
    case "readConfig": return readConfig(call.args.key).output;
    case "listAgents": return listAgents().output;
    case "deleteAgent": return deleteAgent(call.args.agentId).output;
    case "sendEmail": return sendEmail(call.args.to, call.args.subject, call.args.body).output;
  }
}

function main(): void {
  console.log("=".repeat(62));
  console.log("  Agent Assembly — Policy Enforcement Scenario (Node.js)");
  console.log("=".repeat(62));
  console.log();

  console.log(`Policy loaded from policy.yaml  (${POLICY_RULES.length} rules, default: ${DEFAULT_ACTION})`);
  for (const rule of POLICY_RULES) {
    const icon = rule.action === "allow" ? "ALLOW" : "DENY ";
    console.log(`  ${icon}  ${rule.tool.padEnd(14)} — ${rule.reason}`);
  }
  console.log();

  console.log("Running governed tool calls:");
  console.log("-".repeat(44));
  let allowed = 0;
  let denied = 0;
  for (const call of DEMO_CALLS) {
    const argsStr = Object.entries(call.args).map(([k, v]) => `${k}='${v}'`).join(", ");
    console.log(`  → ${call.tool}(${argsStr})`);
    const decision = evaluate(call.tool);
    if (decision.action === "allow") {
      const result = runTool(call);
      console.log(`     ✅ ALLOWED  — ${result}`);
      allowed++;
    } else {
      console.log(`     ❌ DENIED   — ${decision.reason}`);
      denied++;
    }
    console.log();
  }
  console.log(`${allowed + denied} tool calls: ${allowed} allowed, ${denied} denied.`);
}

main();
