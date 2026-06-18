import { MockApprovalClient, POLICY_RULES, DEFAULT_ACTION, evaluate } from "./approval.js";
import { getBalance, transferFunds } from "./tools.js";

type DemoCall =
  | { name: "get_balance"; args: { accountId: string } }
  | { name: "transfer_funds"; args: { fromAccount: string; toAccount: string; amount: number } };

const DEMO_CALLS: DemoCall[] = [
  { name: "get_balance", args: { accountId: "acc-001" } },
  { name: "transfer_funds", args: { fromAccount: "acc-001", toAccount: "acc-002", amount: 500 } },
];

function runTool(call: DemoCall): string {
  switch (call.name) {
    case "get_balance": return getBalance(call.args.accountId).output;
    case "transfer_funds": return transferFunds(call.args.fromAccount, call.args.toAccount, call.args.amount).output;
  }
}

function main(): void {
  console.log("=".repeat(62));
  console.log("  Agent Assembly — Approval Gates Scenario (Node.js)");
  console.log("=".repeat(62));
  console.log();

  const client = new MockApprovalClient(true);

  console.log(`Policy loaded from policy.yaml  (${POLICY_RULES.length} rules, default: ${DEFAULT_ACTION})`);
  for (const rule of POLICY_RULES) {
    console.log(`  ${rule.action.toUpperCase().padEnd(18)} ${rule.tool.padEnd(14)} — ${rule.reason}`);
  }
  console.log();

  console.log("Running governed tool calls:");
  console.log("-".repeat(44));
  let succeeded = 0;
  for (const call of DEMO_CALLS) {
    const argsStr = Object.entries(call.args).map(([k, v]) => `${k}='${v}'`).join(", ");
    console.log(`  → ${call.name}(${argsStr})`);
    const decision = evaluate(call.name, client);
    if (decision.action === "allow") {
      const result = runTool(call);
      console.log(`     ✅ EXECUTED — ${result}`);
      succeeded++;
    } else {
      console.log(`     ❌ BLOCKED  — ${decision.reason}`);
    }
    console.log();
  }

  const immediate = POLICY_RULES.filter(r => r.action === "allow").length;
  const viaApproval = succeeded - immediate;
  console.log(`${DEMO_CALLS.length} tool calls: ${succeeded} succeeded (${immediate} immediate, ${viaApproval} via approval).`);
}

main();
