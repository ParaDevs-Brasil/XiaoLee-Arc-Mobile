"use client";

import React from "react";
import { useTreasury, TreasuryChainBalance } from "@/hooks/useTreasury";
import { CHAIN_LABEL } from "@/lib/chains";
import { useLanguage } from "@/contexts/LanguageContext";
import { IconRefresh } from "@/components/icons";

const CHAIN_ICON: Record<string, string> = {
  arc: "Ξ",
  solana: "◎",
  stellar: "✦",
};

function ChainRow({ b }: { b: TreasuryChainBalance }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="w-8 h-8 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-sm font-bold shrink-0">
        {CHAIN_ICON[b.chain]}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-[var(--ink)] leading-tight">
          {CHAIN_LABEL[b.chain]}
          {b.chain === "arc" && (
            <span className="ml-1.5 text-[9px] font-bold uppercase text-[var(--accent)]">hub</span>
          )}
        </p>
        {b.address && (
          <p className="text-[10px] font-mono text-[var(--ink-3)] truncate" title={b.address}>
            {b.address.slice(0, 10)}…{b.address.slice(-4)}
          </p>
        )}
      </div>
      {b.status === "loading" && (
        <span className="text-xs text-[var(--ink-3)] animate-pulse">…</span>
      )}
      {b.status === "ok" && (
        <div className="text-right">
          <p className="text-sm font-bold text-[var(--ink)]">
            {b.usdcBalance != null ? b.usdcBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}{" "}
            <span className="text-[10px] text-[var(--ink-2)] font-semibold">USDC</span>
          </p>
          {b.sandbox && (
            <span className="text-[9px] font-bold uppercase text-amber-500">sandbox</span>
          )}
        </div>
      )}
      {b.status === "disabled" && (
        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-black/5 text-[var(--ink-3)]">
          disabled
        </span>
      )}
      {b.status === "error" && (
        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--danger)]" title="Backend indisponível">
          offline
        </span>
      )}
    </div>
  );
}

/**
 * Card "Treasury" — saldo USDC da tesouraria por chain, com o Arc como hub
 * (roadmap F1.4). 503 do backend = chain com flag desligada → badge "disabled".
 */
export default function TreasuryCard() {
  const { t } = useLanguage();
  const { balances, loading, refetch } = useTreasury();

  const total = balances
    .filter((b) => b.status === "ok" && b.usdcBalance !== null)
    .reduce((sum, b) => sum + (b.usdcBalance ?? 0), 0);

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] p-5 hover:shadow-sm transition-shadow duration-200">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-base font-bold text-[var(--ink)]">{t("dashboard.treasury_title")}</h3>
        <button
          onClick={refetch}
          disabled={loading}
          title="Atualizar"
          className="p-1.5 rounded-lg text-[var(--ink-3)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-colors disabled:opacity-40"
        >
          <IconRefresh className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>
      <p className="text-xs text-[var(--ink-2)] mb-3">{t("dashboard.treasury_sub")}</p>

      <div className="divide-y divide-[var(--border)]">
        {balances.map((b) => (
          <ChainRow key={b.chain} b={b} />
        ))}
      </div>

      <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--ink-2)]">Total disponível</span>
        <span className="text-sm font-black text-[var(--accent)]">
          {total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDC
        </span>
      </div>
    </div>
  );
}
