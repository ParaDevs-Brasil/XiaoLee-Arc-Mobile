"use client";

import { useCallback, useEffect, useState } from "react";
import api from "../api/api";
import type { Chain } from "@/lib/chains";

/**
 * Saldos da tesouraria XiaoLee por chain (roadmap F1.4 — "Arc como hub").
 *
 *   GET /v1/arc/wallet/balance             → { usdc_balance, sandbox }
 *   GET /v1/cctp/treasury/solana/balance   → { chain, address, usdc_balance, sandbox }
 *   GET /v1/cctp/treasury/stellar/balance  → idem
 *
 * 503 = flag da chain desligada (SOLANA_CCTP_ENABLED etc.) — não é erro:
 * vira status "disabled" e a UI mostra badge, nunca crash.
 */

export type TreasuryStatus = "loading" | "ok" | "disabled" | "error";

export interface TreasuryChainBalance {
  chain: Chain;
  status: TreasuryStatus;
  usdcBalance: number | null;
  address?: string;
  sandbox?: boolean;
}

interface BalancePayload {
  usdc_balance: number;
  sandbox?: boolean;
  address?: string;
}

function statusFromError(err: unknown): TreasuryStatus {
  const status = (err as { response?: { status?: number } })?.response?.status;
  return status === 503 ? "disabled" : "error";
}

async function fetchChainBalance(chain: Chain): Promise<TreasuryChainBalance> {
  const path = chain === "arc" ? "/v1/arc/wallet/balance" : `/v1/cctp/treasury/${chain}/balance`;
  try {
    const resp = await api.get<BalancePayload>(path);
    return {
      chain,
      status: "ok",
      // Stellar treasury não retorna usdc_balance (sem endpoint de saldo no client) — normaliza para null
      usdcBalance: resp.data.usdc_balance ?? null,
      address: resp.data.address,
      sandbox: resp.data.sandbox,
    };
  } catch (err) {
    return { chain, status: statusFromError(err), usdcBalance: null };
  }
}

export function useTreasury() {
  const [balances, setBalances] = useState<TreasuryChainBalance[]>(
    (["arc", "solana", "stellar"] as Chain[]).map((chain) => ({
      chain,
      status: "loading",
      usdcBalance: null,
    })),
  );
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    const results = await Promise.all(
      (["arc", "solana", "stellar"] as Chain[]).map(fetchChainBalance),
    );
    setBalances(results);
    setLoading(false);
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { balances, loading, refetch };
}
