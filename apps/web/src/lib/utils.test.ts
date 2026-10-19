import { describe, expect, it } from "vitest";
import { buildQuery, cn, formatSalary, formatScore } from "./utils";

describe("cn", () => {
  it("merges class names and resolves Tailwind conflicts", () => {
    expect(cn("px-2", "px-4", false && "hidden", "text-sm")).toBe("px-4 text-sm");
  });
});

describe("formatSalary", () => {
  it("returns Czech unknown label when salary is missing", () => {
    expect(formatSalary(null, null, "CZK", "SALARY_UNKNOWN")).toBe("Neuvedeno");
  });

  it("formats a salary range in CZK", () => {
    const result = formatSalary(50000, 70000, "CZK");
    expect(result).toContain("50");
    expect(result).toContain("70");
  });
});

describe("formatScore", () => {
  it("rounds numeric scores", () => {
    expect(formatScore(87.4)).toBe("87");
    expect(formatScore(null)).toBe("—");
  });
});

describe("buildQuery", () => {
  it("skips empty values", () => {
    expect(buildQuery({ a: 1, b: "", c: undefined, d: "x" })).toBe("?a=1&d=x");
  });
});
