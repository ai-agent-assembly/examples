import { describe, expect, it } from "vitest";
import { MockApprovalClient, POLICY_RULES, DEFAULT_ACTION, evaluate } from "../src/approval.js";
import { getBalance, transferFunds } from "../src/tools.js";

describe("policy", () => {
  it("loads policy.yaml with 2 rules", () => {
    expect(POLICY_RULES).toHaveLength(2);
  });

  it("default action is deny", () => {
    expect(DEFAULT_ACTION).toBe("deny");
  });

  it("get_balance action is allow", () => {
    const rule = POLICY_RULES.find((r) => r.tool === "get_balance");
    expect(rule?.action).toBe("allow");
  });

  it("transfer_funds action is approval_required", () => {
    const rule = POLICY_RULES.find((r) => r.tool === "transfer_funds");
    expect(rule?.action).toBe("approval_required");
  });
});

describe("MockApprovalClient", () => {
  it("auto-approves when autoApprove=true", () => {
    const client = new MockApprovalClient(true);
    const id = client.requestApproval("transfer_funds", "{}");
    expect(client.waitForApproval(id)).toBe(true);
  });

  it("rejects when autoApprove=false", () => {
    const client = new MockApprovalClient(false);
    const id = client.requestApproval("transfer_funds", "{}");
    expect(client.waitForApproval(id)).toBe(false);
  });
});

describe("evaluate", () => {
  it("allows get_balance immediately", () => {
    const client = new MockApprovalClient(true);
    expect(evaluate("get_balance", client).action).toBe("allow");
  });

  it("allows transfer_funds after auto-approval", () => {
    const client = new MockApprovalClient(true);
    expect(evaluate("transfer_funds", client).action).toBe("allow");
  });

  it("denies transfer_funds when approval is rejected", () => {
    const client = new MockApprovalClient(false);
    expect(evaluate("transfer_funds", client).action).toBe("deny");
  });

  it("denies unknown tool by default", () => {
    const client = new MockApprovalClient(true);
    expect(evaluate("execute_shell", client).action).toBe("deny");
  });
});

describe("tools", () => {
  it("getBalance returns a dollar amount", () => {
    expect(getBalance("acc-001").output).toMatch(/\$/);
  });

  it("transferFunds returns a confirmation message", () => {
    const result = transferFunds("acc-001", "acc-002", 100);
    expect(result.output).toContain("Transferred");
    expect(result.output).toContain("acc-001");
  });
});
