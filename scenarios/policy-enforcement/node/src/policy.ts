import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import * as yaml from "js-yaml";

const __dirname = dirname(fileURLToPath(import.meta.url));
const POLICY_FILE = resolve(__dirname, "..", "..", "policy.yaml");

export interface PolicyRule {
  tool: string;
  action: "allow" | "deny";
  reason: string;
}

interface PolicyFile {
  rules: PolicyRule[];
  default_action: "allow" | "deny";
  default_reason: string;
}

function loadPolicy(): PolicyFile {
  const content = readFileSync(POLICY_FILE, "utf8");
  return yaml.load(content) as PolicyFile;
}

const _policy = loadPolicy();

export const POLICY_RULES: PolicyRule[] = _policy.rules;
export const DEFAULT_ACTION = _policy.default_action;
export const DEFAULT_REASON = _policy.default_reason;

export function evaluate(toolName: string): PolicyRule {
  const rule = POLICY_RULES.find((r) => r.tool === toolName);
  if (rule) return rule;
  return { tool: toolName, action: DEFAULT_ACTION, reason: DEFAULT_REASON };
}
