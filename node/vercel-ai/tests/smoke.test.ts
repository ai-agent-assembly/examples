import { describe, expect, it } from "vitest";
import { evaluate } from "../src/policy.js";
import { getWeatherTool, sendEmailTool } from "../src/tools.js";

describe("policy", () => {
  it("allows get_weather", () => {
    expect(evaluate("get_weather").action).toBe("allow");
  });

  it("denies send_email", () => {
    expect(evaluate("send_email").action).toBe("deny");
  });

  it("denies any unlisted tool", () => {
    expect(evaluate("transfer_funds").action).toBe("deny");
  });
});

describe("vercel ai tools", () => {
  it("get_weather executes and returns mock output", async () => {
    const out = await getWeatherTool.execute?.(
      { location: "Taipei" },
      { toolCallId: "t1", messages: [], context: {} }
    );
    expect(String(out)).toContain("Taipei");
  });

  it("send_email executes and returns mock output", async () => {
    const out = await sendEmailTool.execute?.(
      { to: "ops@example.com", body: "hi" },
      { toolCallId: "t2", messages: [], context: {} }
    );
    expect(String(out)).toContain("ops@example.com");
  });
});
