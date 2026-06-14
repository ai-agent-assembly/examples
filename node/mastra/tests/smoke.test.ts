import { describe, expect, it } from "vitest";
import { evaluate } from "../src/policy.js";
import { getStockPriceTool, placeTradeTool } from "../src/tools.js";

function runTool(
  tool: { execute?: ((inputData: never, context: never) => Promise<unknown>) | undefined },
  input: Record<string, unknown>
): Promise<unknown> {
  if (!tool.execute) throw new Error("tool has no execute function");
  return tool.execute(input as never, {} as never);
}

describe("policy", () => {
  it("allows get_stock_price", () => {
    expect(evaluate("get_stock_price").action).toBe("allow");
  });

  it("denies place_trade", () => {
    expect(evaluate("place_trade").action).toBe("deny");
  });

  it("denies any unlisted tool", () => {
    expect(evaluate("wire_transfer").action).toBe("deny");
  });
});

describe("mastra tools", () => {
  it("get_stock_price executes and returns mock output", async () => {
    const out = await runTool(getStockPriceTool, { ticker: "AASM" });
    expect(JSON.stringify(out)).toContain("AASM");
  });

  it("place_trade executes and returns mock output", async () => {
    const out = await runTool(placeTradeTool, { ticker: "AASM", shares: 10 });
    expect(JSON.stringify(out)).toContain("10 shares");
  });
});
