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
