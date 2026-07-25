import { describe, expect, it } from "vitest";

import { fromRawAmount, getQuoteSummary, toRawAmount } from "./swap";

describe("swap utils", () => {
  it("converts ui amount to raw amount with decimals", () => {
    expect(toRawAmount(1.25, 6)).toBe(1250000);
    expect(toRawAmount(0, 6)).toBe(0);
  });

  it("converts raw amount to ui amount", () => {
    expect(fromRawAmount("42000000", 6)).toBe(42);
    expect(fromRawAmount(undefined, 6)).toBe(0);
  });

  it("extracts quote summary safely", () => {
    const summary = getQuoteSummary(
      {
        outAmount: "123000000",
        otherAmountThreshold: "120000000",
        priceImpactPct: "0.15",
        slippageBps: 50,
        routePlan: [{}, {}],
      },
      6,
    );

    expect(summary.outAmountUi).toBe(123);
    expect(summary.minOutAmountUi).toBe(120);
    expect(summary.priceImpactPct).toBeCloseTo(0.15);
    expect(summary.slippageBps).toBe(50);
    expect(summary.routeHops).toBe(2);
  });
});
