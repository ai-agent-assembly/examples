import type { GatewayClient } from "@agent-assembly/sdk";

export interface PolicyRule {
  tool: string;
  action: "allow" | "deny";
  reason: string;
}

export const POLICY_RULES: PolicyRule[] = [
  {
    tool: "read_file",
    action: "allow",
    reason: "Read-only file access is safe to execute.",
  },
  {
    tool: "write_file",
    action: "deny",
    reason: "Write operations to the filesystem require explicit approval.",
  },
];

export function evaluate(toolName: string): PolicyRule {
  const rule = POLICY_RULES.find((r) => r.tool === toolName);
  if (rule) return rule;
  return { tool: toolName, action: "deny", reason: "Unlisted tool — deny by default." };
}

/**
 * Build a GatewayClient that enforces this example's local policy in-process,
 * so withAssembly can govern tool calls offline — no running gateway required.
 */
export function createPolicyGatewayClient(): GatewayClient {
  return {
    mode: "sdk-only",
    start: async () => undefined,
    close: async () => undefined,
    check: async (request) => {
      const rule = evaluate(request.toolName ?? "");
      return rule.action === "deny"
        ? { denied: true, reason: rule.reason }
        : { denied: false };
    },
    waitForApproval: async () => ({ denied: false }),
    record: async () => undefined,
    recordResult: async () => undefined,
    scanPrompts: async () => undefined
  };
}
