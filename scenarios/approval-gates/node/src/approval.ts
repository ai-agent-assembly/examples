import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import yaml from "js-yaml";

const __dirname = dirname(fileURLToPath(import.meta.url));
const POLICY_FILE = resolve(__dirname, "..", "..", "policy.yaml");

export interface PolicyRule {
  tool: string;
  action: "allow" | "deny" | "approval_required";
  reason: string;
}

interface PolicyFile {
  rules: PolicyRule[];
  default_action: "allow" | "deny";
  default_reason: string;
}

function loadPolicy(): PolicyFile {
  const content = readFileSync(POLICY_FILE, "utf8");
  // Use CORE_SCHEMA (strings, numbers, booleans only) — never DEFAULT_SCHEMA,
  // which includes !!js/function and !!js/regexp tags that can execute code.
  return yaml.load(content, { schema: yaml.CORE_SCHEMA }) as PolicyFile;
}

const _policy = loadPolicy();

export const POLICY_RULES: PolicyRule[] = _policy.rules;
export const DEFAULT_ACTION = _policy.default_action;
export const DEFAULT_REASON = _policy.default_reason;

export class MockApprovalClient {
  private readonly autoApprove: boolean;
  private counter = 0;

  constructor(autoApprove = true) {
    this.autoApprove = autoApprove;
  }

  requestApproval(toolName: string, _context: string): string {
    this.counter++;
    const requestId = `mock-req-${String(this.counter).padStart(3, "0")}`;
    console.log(`     ⏳ PENDING  — approval required for '${toolName}'`);
    return requestId;
  }

  waitForApproval(requestId: string): boolean {
    if (this.autoApprove) {
      console.log(`     ✅ APPROVED — MockApprovalClient auto-approved (request_id='${requestId}')`);
      return true;
    }
    console.log(`     ❌ REJECTED — MockApprovalClient rejected (request_id='${requestId}')`);
    return false;
  }
}

export type Decision =
  | { action: "allow"; reason: string }
  | { action: "deny"; reason: string };

export function evaluate(toolName: string, client: MockApprovalClient): Decision {
  const rule = POLICY_RULES.find((r) => r.tool === toolName) ?? {
    tool: toolName,
    action: DEFAULT_ACTION,
    reason: DEFAULT_REASON,
  };

  if (rule.action === "allow") {
    return { action: "allow", reason: rule.reason };
  }

  if (rule.action === "approval_required") {
    const requestId = client.requestApproval(toolName, toolName);
    const approved = client.waitForApproval(requestId);
    if (approved) {
      return { action: "allow", reason: `Approved (request_id='${requestId}')` };
    }
    return { action: "deny", reason: "Approval request was rejected" };
  }

  return { action: "deny", reason: rule.reason };
}
