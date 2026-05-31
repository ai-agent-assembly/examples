import { evaluate, POLICY_RULES, DEFAULT_ACTION } from "./policy.js";
import { readConfig, listAgents, deleteAgent, sendEmail } from "./tools.js";

type DemoCall =
  | { name: "readConfig"; args: { key: string } }
  | { name: "listAgents"; args: Record<string, never> }
  | { name: "deleteAgent"; args: { agentId: string } }
  | { name: "sendEmail"; args: { to: string; subject: string; body: string } };

const DEMO_CALLS: DemoCall[] = [
  { name: "readConfig", args: { key: "database.host" } },
  { name: "listAgents", args: {} },
  { name: "deleteAgent", args: { agentId: "agent-001" } },
  { name: "sendEmail", args: { to: "admin@example.com", subject: "Hello", body: "Test message" } },
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
    console.log(`  → ${call.name}(${argsStr})`);
    const decision = evaluate(call.name);
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
