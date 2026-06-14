import { describe, expect, it } from "vitest";
import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "../src/policy.js";

describe("withAssembly governance", () => {
  it("allows read_file through the policy gateway client", async () => {
    const tools = withAssembly(
      { read_file: { execute: async () => "ran" } },
      { gatewayClient: createPolicyGatewayClient() }
    );
    expect(await tools.read_file.execute()).toBe("ran");
  });

  it("blocks write_file with PolicyViolationError", async () => {
    const tools = withAssembly(
      { write_file: { execute: async () => "ran" } },
      { gatewayClient: createPolicyGatewayClient() }
    );
    await expect(tools.write_file.execute()).rejects.toBeInstanceOf(PolicyViolationError);
  });
});
