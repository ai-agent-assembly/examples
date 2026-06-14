import { describe, expect, it } from "vitest";
import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "../src/policy.js";

describe("withAssembly governance", () => {
  it("allows search_web through the policy gateway client", async () => {
    const tools = withAssembly(
      { search_web: { execute: async () => "ran" } },
      { gatewayClient: createPolicyGatewayClient() }
    );
    expect(await tools.search_web.execute()).toBe("ran");
  });

  it("blocks send_email with PolicyViolationError", async () => {
    const tools = withAssembly(
      { send_email: { execute: async () => "ran" } },
      { gatewayClient: createPolicyGatewayClient() }
    );
    await expect(tools.send_email.execute()).rejects.toBeInstanceOf(PolicyViolationError);
  });
});
