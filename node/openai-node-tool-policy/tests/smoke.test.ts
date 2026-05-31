import { describe, expect, it } from "vitest";
import { evaluate } from "../src/policy.js";
import { TOOL_DEFINITIONS, searchWeb, sendEmail } from "../src/tools.js";

describe("policy", () => {
  it("allows search_web", () => {
    expect(evaluate("search_web").action).toBe("allow");
  });

  it("denies send_email", () => {
    expect(evaluate("send_email").action).toBe("deny");
  });

  it("denies unknown tools by default", () => {
    expect(evaluate("rm_rf").action).toBe("deny");
  });
});

describe("tool definitions", () => {
  it("exports two OpenAI-format tool definitions", () => {
    expect(TOOL_DEFINITIONS).toHaveLength(2);
    for (const t of TOOL_DEFINITIONS) {
      expect(t.type).toBe("function");
      expect(t.function.name).toBeTruthy();
    }
  });
});

describe("tool implementations", () => {
  it("searchWeb returns mock results containing the query", () => {
    const result = searchWeb("Agent Assembly");
    expect(result.allowed).toBe(true);
    expect(result.output).toContain("Agent Assembly");
  });

  it("sendEmail returns blocked message", () => {
    const result = sendEmail("user@example.com", "Hello");
    expect(result.allowed).toBe(false);
    expect(result.output).toContain("BLOCKED");
  });
});
