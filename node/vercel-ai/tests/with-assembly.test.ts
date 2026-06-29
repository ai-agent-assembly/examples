import { describe, expect, it } from "vitest";
import { PolicyViolationError, withAssembly } from "@agent-assembly/sdk";
import { createPolicyGatewayClient } from "../src/policy.js";
import { getWeatherTool, sendEmailTool } from "../src/tools.js";

describe("withAssembly governance over Vercel AI SDK tools", () => {
  it("allows get_weather through the policy gateway client", async () => {
    const tools = withAssembly(
      { get_weather: getWeatherTool },
      { gatewayClient: createPolicyGatewayClient() }
    );
    const out = await tools.get_weather.execute?.(
      { location: "Taipei" },
      { toolCallId: "t1", messages: [], context: {} }
    );
    expect(String(out)).toContain("Taipei");
  });

  it("blocks send_email with PolicyViolationError", async () => {
    const tools = withAssembly(
      { send_email: sendEmailTool },
      { gatewayClient: createPolicyGatewayClient() }
    );
    await expect(
      tools.send_email.execute?.(
        { to: "ops@example.com", body: "leak" },
        { toolCallId: "t2", messages: [], context: {} }
      )
    ).rejects.toBeInstanceOf(PolicyViolationError);
  });
});
