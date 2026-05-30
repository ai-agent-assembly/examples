export interface PolicyRule {
  tool: string;
  action: "allow" | "deny";
  reason: string;
}

export const POLICY_RULES: PolicyRule[] = [
  {
    tool: "search_web",
    action: "allow",
    reason: "Read-only search — safe to execute without approval.",
  },
  {
    tool: "send_email",
    action: "deny",
    reason: "External communication requires human approval before sending.",
  },
];

export function evaluate(toolName: string): PolicyRule {
  const rule = POLICY_RULES.find((r) => r.tool === toolName);
  if (rule) return rule;
  return { tool: toolName, action: "deny", reason: "No matching policy rule — deny by default." };
}
