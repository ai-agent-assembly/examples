import { describe, expect, it } from "vitest";
import { evaluate, POLICY_RULES, DEFAULT_ACTION } from "../src/policy.js";
import { readConfig, listAgents, deleteAgent } from "../src/tools.js";

describe("policy", () => {
  it("loads policy.yaml with 4 rules", () => {
    expect(POLICY_RULES).toHaveLength(4);
  });

  it("default action is deny", () => {
    expect(DEFAULT_ACTION).toBe("deny");
  });

  it("allows read_config", () => {
    expect(evaluate("read_config").action).toBe("allow");
  });

  it("allows list_agents", () => {
    expect(evaluate("list_agents").action).toBe("allow");
  });

  it("denies delete_agent", () => {
    expect(evaluate("delete_agent").action).toBe("deny");
  });

  it("denies send_email", () => {
    expect(evaluate("send_email").action).toBe("deny");
  });

  it("denies any unlisted tool by default", () => {
    expect(evaluate("execute_shell").action).toBe("deny");
  });
});

describe("tools", () => {
  it("readConfig returns a value", () => {
    const result = readConfig("database.host");
    expect(result.allowed).toBe(true);
    expect(result.output).toContain("localhost");
  });

  it("listAgents returns agent list", () => {
    const result = listAgents();
    expect(result.allowed).toBe(true);
    expect(JSON.parse(result.output)).toHaveLength(3);
  });

  it("deleteAgent returns deleted message", () => {
    const result = deleteAgent("agent-001");
    expect(result.output).toContain("Deleted");
  });
});
