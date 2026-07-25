export type SwapTokenOption = {
  symbol: string;
  mint: string;
  decimals: number;
};

export const SWAP_TOKEN_OPTIONS: SwapTokenOption[] = [
  {
    symbol: "USDC",
    mint: "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
    decimals: 6,
  },
  {
    symbol: "SOL",
    mint: "So11111111111111111111111111111111111111112",
    decimals: 9,
  },
];

export function toRawAmount(uiAmount: number, decimals: number): number {
  if (!Number.isFinite(uiAmount) || uiAmount <= 0) return 0;
  return Math.round(uiAmount * 10 ** decimals);
}

export function fromRawAmount(rawAmount: string | number | null | undefined, decimals: number): number {
  if (rawAmount === null || rawAmount === undefined) return 0;
  const asNumber = typeof rawAmount === "number" ? rawAmount : Number(rawAmount);
  if (!Number.isFinite(asNumber)) return 0;
  return asNumber / 10 ** decimals;
}

export type QuoteSummary = {
  outAmountUi: number;
  priceImpactPct: number;
  minOutAmountUi: number;
  routeHops: number;
  slippageBps: number;
};

function asFiniteNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function getQuoteSummary(quote: unknown, outputDecimals: number): QuoteSummary {
  if (!quote || typeof quote !== "object") {
    return {
      outAmountUi: 0,
      priceImpactPct: 0,
      minOutAmountUi: 0,
      routeHops: 0,
      slippageBps: 0,
    };
  }

  const record = quote as Record<string, unknown>;
  const outAmountUi = fromRawAmount(record.outAmount as string | number | null | undefined, outputDecimals);
  const minOutAmountUi = fromRawAmount(
    record.otherAmountThreshold as string | number | null | undefined,
    outputDecimals,
  );
  const priceImpactPct = asFiniteNumber(record.priceImpactPct, 0);
  const routePlan = asArray(record.routePlan);
  const slippageBps = asFiniteNumber(record.slippageBps, 0);

  return {
    outAmountUi,
    priceImpactPct,
    minOutAmountUi,
    routeHops: routePlan.length,
    slippageBps,
  };
}
