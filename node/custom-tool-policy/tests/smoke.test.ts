import { describe, expect, it } from "vitest";
import { evaluate } from "../src/policy.js";
import { readFile, writeFile } from "../src/tools.js";

describe("policy", () => {
  it("allows read_file", () => {
    expect(evaluate("read_file").action).toBe("allow");
  });

  it("denies write_file", () => {
    expect(evaluate("write_file").action).toBe("deny");
  });

  it("denies any unlisted tool", () => {
    expect(evaluate("exec_shell").action).toBe("deny");
  });
});

describe("tools", () => {
  it("readFile returns allowed result with path in output", () => {
    const result = readFile("/data/report.txt");
    expect(result.allowed).toBe(true);
    expect(result.output).toContain("/data/report.txt");
  });

  it("writeFile returns blocked result", () => {
    const result = writeFile("/etc/config", "override");
    expect(result.allowed).toBe(false);
    expect(result.output).toContain("BLOCKED");
  });
});
