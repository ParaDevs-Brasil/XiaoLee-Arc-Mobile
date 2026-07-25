"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Navbar from "../../components/navbar/Navbar";
import { ThemeProviderWrapper } from "@/providers/ThemeProvider";
import { useLanguage } from "@/contexts/LanguageContext";
import {
  IconDollar, IconZap, IconUsers, IconActivity, IconCheck,
  IconInbox, IconUserPlus,
} from "@/components/icons";

const API = process.env.NEXT_PUBLIC_CORE_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────
interface PaymentEvent {
  intent_id: string;
  amount: number;
  creator: string;
  tx: string;
  ts: string;
  latency_ms: number;
}

interface TractionSnapshot {
  total_usdc: number;
  total_payments: number;
  active_creators: number;
  registered_creators: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  feed: PaymentEvent[];
}

const EMPTY: TractionSnapshot = {
  total_usdc: 0,
  total_payments: 0,
  active_creators: 0,
  registered_creators: 0,
  avg_latency_ms: 0,
  p95_latency_ms: 0,
  feed: [],
};

// ── Helpers ────────────────────────────────────────────────────────────────
function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}min ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function formatUSDC(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── Stat card ──────────────────────────────────────────────────────────────
function StatCard({
  Icon,
  value,
  label,
  accent,
  bg,
  border,
  sub,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  value: string;
  label: string;
  accent: string;
  bg: string;
  border: string;
  sub?: string;
}) {
  return (
    <div className={`rounded-2xl border ${border} ${bg} p-5 flex flex-col gap-2`}>
      <div className={`flex items-center gap-2 ${accent}`}>
        <Icon className="w-5 h-5" />
        <span className="text-xs font-bold uppercase tracking-widest">{label}</span>
      </div>
      <div className="text-3xl font-black text-[var(--text-primary)] leading-none">{value}</div>
      {sub && <div className="text-xs text-gray-500 font-medium">{sub}</div>}
    </div>
  );
}

// ── Latency bar ────────────────────────────────────────────────────────────
function LatencyBar({ avg, p95 }: { avg: number; p95: number }) {
  const { t } = useLanguage();
  const ok = avg < 500;
  return (
    <div className={`rounded-2xl border p-4 flex items-center gap-3 ${ok ? "border-emerald-100 bg-emerald-50" : "border-amber-100 bg-amber-50"}`}>
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${ok ? "text-[var(--success)] bg-emerald-100" : "text-amber-500 bg-amber-100"}`}>
        <IconZap className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-bold ${ok ? "text-[var(--success)]" : "text-amber-700"}`}>
          {ok ? t("traction.latency_ok") : t("traction.latency_degraded")}
          {" · "}
          <span className="font-black">{avg.toFixed(0)}ms avg</span>
          {p95 > 0 && <span className="font-medium text-gray-500 ml-1">· P95 {p95.toFixed(0)}ms</span>}
        </div>
        <div className="text-xs text-gray-500 mt-0.5">{t("traction.latency_sub")}</div>
      </div>
      <div className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold ${ok ? "bg-[var(--success)] text-white" : "bg-amber-500 text-white"}`}>
        <IconCheck className="w-3 h-3" />
        {ok ? t("traction.latency_fast") : t("traction.latency_slow")}
      </div>
    </div>
  );
}

// ── Feed item ──────────────────────────────────────────────────────────────
function FeedItem({ event, isNew }: { event: PaymentEvent; isNew: boolean }) {
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300 ${isNew ? "border-emerald-100 bg-emerald-50/60" : "border-[var(--border)] bg-white"}`}>
      <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center shrink-0 text-[var(--success)]">
        <IconDollar className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-700 truncate">
          Agent paid{" "}
          <span className="text-[var(--success)] font-black">${event.amount.toFixed(2)} USDC</span>
          {" to "}
          <span className="text-[var(--accent)] font-bold">{event.creator}</span>
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[10px] text-gray-400 font-mono truncate max-w-[120px]">{event.tx.slice(0, 14)}…</span>
          <span className="text-[10px] text-gray-400">·</span>
          <span className="text-[10px] text-gray-400">{event.latency_ms.toFixed(0)}ms</span>
        </div>
      </div>
      <span className="text-[10px] text-gray-400 shrink-0 whitespace-nowrap">{timeAgo(event.ts)}</span>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function TractionPage() {
  const { t } = useLanguage();
  const [snap, setSnap] = useState<TractionSnapshot>(EMPTY);
  const [feed, setFeed] = useState<PaymentEvent[]>([]);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let pollInterval: ReturnType<typeof setInterval> | null = null;

    function startPolling() {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`${API}/v1/traction/stats`);
          if (!res.ok) return;
          const data: TractionSnapshot = await res.json();
          setSnap(data);
          setFeed(data.feed ?? []);
        } catch {
          // silently ignore
        }
      }, 5000);
    }

    try {
      const es = new EventSource(`${API}/v1/traction/feed`);
      esRef.current = es;

      es.onopen = () => setConnected(true);

      es.addEventListener("snapshot", (e) => {
        try {
          const data: TractionSnapshot = JSON.parse(e.data);
          setSnap(data);
          setFeed(data.feed ?? []);
        } catch {}
      });

      es.addEventListener("payment_settled", (e) => {
        try {
          const event: PaymentEvent = JSON.parse(e.data);
          setSnap((prev) => ({
            ...prev,
            total_usdc: prev.total_usdc + event.amount,
            total_payments: prev.total_payments + 1,
          }));
          setFeed((prev) => [event, ...prev].slice(0, 20));
          setNewIds((prev) => new Set(prev).add(event.intent_id));
          setTimeout(() => {
            setNewIds((prev) => {
              const s = new Set(prev);
              s.delete(event.intent_id);
              return s;
            });
          }, 4000);
        } catch {}
      });

      es.onerror = () => {
        setConnected(false);
        es.close();
        startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      esRef.current?.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, []);

  return (
    <ThemeProviderWrapper>
      <div className="min-h-screen bg-[var(--main-bg)] transition-colors duration-500">
        <Navbar />

        <main className="container mx-auto px-4 py-10 max-w-2xl lg:max-w-4xl">

          {/* ── Header ──────────────────────────────────────────────── */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-3">
              <h1 className="text-3xl font-extrabold text-[var(--text-primary)] leading-tight">
                {t("traction.title")}
              </h1>
              <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${connected ? "bg-[var(--success)] animate-pulse" : "bg-gray-300"}`} />
            </div>
            <p className="text-sm text-gray-500 max-w-xs mx-auto leading-relaxed">
              {t("traction.subtitle")}
            </p>
          </div>

          {/* ── Stats grid ──────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
            <StatCard
              Icon={IconDollar}
              value={`$${formatUSDC(snap.total_usdc)}`}
              label={t("traction.usdc_paid")}
              accent="text-[var(--success)]"
              bg="bg-white"
              border="border-[var(--border)]"
              sub={t("traction.usdc_paid_sub")}
            />
            <StatCard
              Icon={IconZap}
              value={String(snap.total_payments)}
              label={t("traction.payments")}
              accent="text-[var(--accent)]"
              bg="bg-white"
              border="border-[var(--border)]"
              sub={t("traction.payments_sub")}
            />
            <StatCard
              Icon={IconUsers}
              value={String(snap.active_creators)}
              label={t("traction.paid_creators")}
              accent="text-[var(--text-secondary)]"
              bg="bg-white"
              border="border-[var(--border)]"
              sub={t("traction.paid_creators_sub")}
            />
            <StatCard
              Icon={IconUserPlus}
              value={String(snap.registered_creators)}
              label={t("traction.registered_creators")}
              accent="text-[var(--text-secondary)]"
              bg="bg-white"
              border="border-[var(--border)]"
              sub={t("traction.registered_creators_sub")}
            />
          </div>

          {/* ── Latency bar ─────────────────────────────────────────── */}
          <div className="mb-4">
            <LatencyBar avg={snap.avg_latency_ms} p95={snap.p95_latency_ms} />
          </div>

          {/* ── Creator CTA ─────────────────────────────────────────── */}
          <Link
            href="/onboarding"
            className="flex items-center justify-between px-5 py-4 rounded-2xl border border-[var(--border)] bg-[var(--accent-soft)] hover:bg-[#fbe3ef] transition-all duration-200 group mb-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white text-[var(--accent)] border border-[var(--border)] flex items-center justify-center shrink-0">
                <IconUserPlus className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-gray-700">{t("traction.cta_creator_title")}</p>
                <p className="text-xs text-gray-500">{t("traction.cta_creator_sub")}</p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs font-bold text-[var(--accent)] group-hover:translate-x-1 transition-transform">
              {t("traction.cta_creator_join")}
              <IconArrowRight />
            </div>
          </Link>

          {/* ── Live feed ───────────────────────────────────────────── */}
          <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <span className="text-[var(--accent)]"><IconActivity className="w-4 h-4" /></span>
                <div>
                  <h2 className="text-sm font-bold text-gray-700">{t("traction.feed_title")}</h2>
                  <p className="text-xs text-gray-500">{t("traction.feed_sub")}</p>
                </div>
              </div>
              <div className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg ${connected ? "text-[var(--success)] bg-emerald-50 border border-emerald-100" : "text-gray-500 bg-gray-50 border border-gray-100"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-[var(--success)]" : "bg-gray-400"}`} />
                {connected ? t("traction.sse_live") : t("traction.polling")}
              </div>
            </div>

            <div className="p-4 flex flex-col gap-2">
              {feed.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <div className="text-[var(--text-placeholder)] mb-3"><IconInbox className="w-6 h-6" /></div>
                  <p className="text-xs font-semibold text-gray-500">{t("traction.feed_empty")}</p>
                  <p className="text-xs text-gray-400 mt-1 max-w-xs">{t("traction.feed_empty_sub")}</p>
                </div>
              ) : (
                feed.map((ev) => (
                  <FeedItem key={ev.intent_id} event={ev} isNew={newIds.has(ev.intent_id)} />
                ))
              )}
            </div>
          </div>

          {/* ── Footer ──────────────────────────────────────────────── */}
          <p className="text-center text-xs text-gray-400 font-medium uppercase tracking-widest mt-8">
            {t("traction.footer")}
          </p>

        </main>
      </div>
    </ThemeProviderWrapper>
  );
}

function IconArrowRight() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
      <path d="M5 12h14m-7-7 7 7-7 7"/>
    </svg>
  );
}
