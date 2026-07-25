import React, { useState } from "react";
import { TransacoesProps, SwapHistoryItem, TransactionHistoryItem } from "@/interfaces";
import { formatDate } from "@/utils/formatters";
import { useModal } from "@/hooks/useModal";
import UserData from "@/components/UserData";
import { useLanguage } from "@/contexts/LanguageContext";

// ── SVG Icons ─────────────────────────────────────────────────────────────────
const IconRefresh = ({ spinning }: { spinning?: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"
    className={`w-4 h-4 ${spinning ? "animate-spin" : ""}`}>
    <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
  </svg>
);
const IconClose = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);
const IconSwap = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="M7 16V4m0 0L3 8m4-4l4 4" /><path d="M17 8v12m0 0l4-4m-4 4l-4-4" />
  </svg>
);
const IconTx = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <path d="M14 2H6a2 2 0 0 0-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 0 0-2-2z" />
  </svg>
);
const IconAll = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);
const IconShield = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);
const IconCheck = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const IconClock = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);

// ── Types ──────────────────────────────────────────────────────────────────────
interface DisplayActivity {
  type: "swap" | "transaction";
  id: string;
  description: string;
  timestamp: string;
  status: string;
  data: SwapHistoryItem | TransactionHistoryItem;
}

type ActivityTab = "all" | "swaps" | "transactions";

// ── Component ──────────────────────────────────────────────────────────────────
const Transacoes: React.FC<TransacoesProps> = ({ transactions = [], shouldOpen = false, onClose }) => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<ActivityTab>("all");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [, setRefreshTrigger] = useState(0);
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);

  const history = UserData.getHistory();
  const swaps = history.swaps || [];
  const internalTransactions = history.transactions || [];

  React.useEffect(() => {
    const handler = () => setRefreshTrigger((p) => p + 1);
    if (typeof window !== "undefined") {
      window.addEventListener("userDataLoaded", handler);
      return () => window.removeEventListener("userDataLoaded", handler);
    }
  }, []);

  const getInternalTransactions = (): TransactionHistoryItem[] => {
    const raw = UserData.getTransactionHistory() as TransactionHistoryItem[];
    return raw?.length ? raw : internalTransactions;
  };

  const getAllActivities = (): DisplayActivity[] => {
    const activities: DisplayActivity[] = [];

    swaps.forEach((swap: SwapHistoryItem, index: number) => {
      activities.push({
        type: "swap",
        id: `swap-${index}`,
        description: `${swap.transaction_type}: ${swap.amount} ${swap.token}`,
        timestamp: swap.timestamp,
        status: swap.status,
        data: swap,
      });
    });

    transactions.forEach((tx: TransactionHistoryItem) => {
      activities.push({
        type: "transaction",
        id: tx.id.toString(),
        description: `${tx.transaction_type}: ${tx.amount} ${tx.token_symbol}`,
        timestamp: tx.created_at,
        status: tx.status,
        data: tx,
      });
    });

    getInternalTransactions().forEach((tx: TransactionHistoryItem) => {
      if (tx.amount && tx.token_symbol) {
        activities.push({
          type: "transaction",
          id: tx.id.toString(),
          description: `${tx.transaction_type}: ${tx.amount} ${tx.token_symbol}`,
          timestamp: tx.created_at,
          status: tx.status,
          data: tx,
        });
      }
    });

    return activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  };

  const getFilteredActivities = () => {
    const all = getAllActivities();
    if (activeTab === "swaps") return all.filter((a) => a.type === "swap");
    if (activeTab === "transactions") return all.filter((a) => a.type === "transaction");
    return all;
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await UserData.fetchData();
      setRefreshTrigger((p) => p + 1);
    } catch (e) {
      console.error("Error refreshing transaction data:", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  const allActivities = getAllActivities();
  const swapCount = allActivities.filter((a) => a.type === "swap").length;
  const txCount = allActivities.filter((a) => a.type === "transaction").length;

  const tabs: { key: ActivityTab; label: string; Icon: React.FC; count: number }[] = [
    { key: "all", label: t('transacoes.tab_all'), Icon: IconAll, count: allActivities.length },
    { key: "swaps", label: t('transacoes.tab_swaps'), Icon: IconSwap, count: swapCount },
    { key: "transactions", label: t('transacoes.tab_transactions'), Icon: IconTx, count: txCount },
  ];

  return (
    <>
      {isOpen && (
        <div
          className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${
            animateIn ? "bg-black/40 backdrop-blur-md" : "bg-black/0"
          }`}
          onClick={closeModal}
        >
          <div
            className={`relative bg-white rounded-3xl shadow-e3 border border-[var(--border)] max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col transition-all duration-300 transform ${
              animateIn ? "scale-100 opacity-100 translate-y-0" : "scale-95 opacity-0 translate-y-4"
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            {/* ── Floating decorative elements ── */}
            <div className="absolute bottom-14 right-10 text-base animate-pulse pointer-events-none select-none z-0 opacity-50">💎</div>

            {/* ── Header ── */}
            <div className="px-6 pt-6 pb-4 border-b border-[var(--border)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-2xl bg-[var(--accent)] text-white shadow-e2 flex items-center justify-center">
                    <IconTx />
                  </div>
                  <div>
                    <h2 className="text-2xl font-extrabold text-[var(--ink)] leading-tight">
                      {t('transacoes.title')}
                    </h2>
                    <p className="text-xs text-[var(--ink-2)] font-medium mt-0.5">
                      {t('transacoes.subtitle')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="p-2 rounded-xl text-[var(--ink-3)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all duration-200 disabled:opacity-40"
                    title="Refresh"
                  >
                    <IconRefresh spinning={isRefreshing} />
                  </button>
                  <button
                    onClick={closeModal}
                    className="p-2 rounded-xl text-[var(--ink-3)] hover:text-[var(--ink)] hover:bg-black/5 transition-all duration-200"
                    title="Close"
                  >
                    <IconClose />
                  </button>
                </div>
              </div>
            </div>

            {/* ── Stats row ── */}
            <div className="grid grid-cols-3 gap-3 px-6 py-4">
              {[
                { label: t('transacoes.tab_all'), value: allActivities.length },
                { label: t('transacoes.tab_swaps'), value: swapCount },
                { label: t('transacoes.tab_transactions'), value: txCount },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-2xl bg-[var(--bg)] border border-[var(--border)] p-3 text-center shadow-e1">
                  <div className="text-3xl font-black text-[var(--accent)] leading-none">
                    {value}
                  </div>
                  <div className="text-xs text-[var(--ink-2)] mt-1 font-semibold">{label}</div>
                </div>
              ))}
            </div>

            {/* ── Tabs ── */}
            <div className="px-6 pb-3">
              <div className="flex gap-2 p-1 bg-white border border-[var(--border)] rounded-2xl shadow-e1">
                {tabs.map(({ key, label, Icon, count }) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                      activeTab === key
                        ? "bg-[var(--accent)] text-white shadow-e2"
                        : "text-[var(--ink-2)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)]"
                    }`}
                  >
                    <Icon />
                    <span>{label}</span>
                    {count > 0 && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-full font-bold ${
                        activeTab === key ? "bg-white/30 text-white" : "bg-[var(--accent-soft)] text-[var(--accent)]"
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Content ── */}
            <div className="flex-1 overflow-y-auto px-6 pb-4 min-h-0">
              {(() => {
                const filtered = getFilteredActivities();
                if (filtered.length === 0) {
                  return (
                    <div className="flex flex-col items-center justify-center py-14 text-center">
                      <div className="text-7xl mb-5">
                        {activeTab === "swaps" ? "🔄" : activeTab === "transactions" ? "💸" : "🐣"}
                      </div>
                      <h3 className="text-xl font-bold text-[var(--ink)] mb-2">
                        {activeTab === "swaps"
                          ? t('transacoes.empty_swaps')
                          : activeTab === "transactions"
                          ? t('transacoes.empty_transactions')
                          : t('transacoes.empty_all')}
                      </h3>
                      <p className="text-sm text-[var(--ink-2)] mb-4">
                        {t('transacoes.empty_sub')}
                      </p>
                      <div className="flex gap-2 text-lg">
                        <span className="animate-bounce">💫</span>
                        <span className="animate-bounce delay-100">🌸</span>
                        <span className="animate-bounce delay-200">💕</span>
                      </div>
                    </div>
                  );
                }

                return (
                  <div className="space-y-2.5">
                    {filtered.map((activity) => {
                      const isSwap = activity.type === "swap";
                      const isCompleted = activity.status === "completed";
                      const swapData = activity.data as SwapHistoryItem;
                      const txData = activity.data as TransactionHistoryItem;

                      return (
                        <div
                          key={`${activity.type}-${activity.id}`}
                          className="group rounded-2xl border border-[var(--border)] bg-white p-4 shadow-e1 hover:shadow-e2 hover:border-[var(--accent)]/40 transition-all duration-200 hover:-translate-y-0.5"
                        >
                          <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                              isSwap
                                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                                : "bg-black/5 text-[var(--ink-2)]"
                            }`}>
                              {isSwap ? <IconSwap /> : <IconTx />}
                            </div>

                            {/* Body */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <span className="font-semibold text-[var(--ink)] text-sm truncate">
                                  {isSwap
                                    ? `${swapData.transaction_type}: ${swapData.amount} ${swapData.token}`
                                    : `${txData.transaction_type}: ${txData.amount} ${txData.token_symbol}`}
                                </span>
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold flex-shrink-0 ${
                                  isCompleted
                                    ? "bg-emerald-50 text-emerald-600 border border-emerald-100"
                                    : "bg-amber-50 text-amber-600 border border-amber-100"
                                }`}>
                                  {isCompleted ? <IconCheck /> : <IconClock />}
                                  {activity.status}
                                </span>
                              </div>

                              <div className="flex items-center justify-between gap-2">
                                <span className="text-xs text-[var(--ink-3)] font-medium">
                                  {formatDate(activity.timestamp)}
                                </span>
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
                                  isSwap
                                    ? "bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--border)]"
                                    : "bg-black/5 text-[var(--ink-2)] border-[var(--border)]"
                                }`}>
                                  {isSwap ? t('transacoes.type_swap') : t('transacoes.type_transaction')}
                                </span>
                              </div>

                              {isSwap && swapData.to_address && (
                                <p className="text-xs text-[var(--ink-3)] font-mono mt-1 truncate">
                                  → {swapData.to_address}
                                </p>
                              )}
                              {!isSwap && txData.sender_twitter_handle && (
                                <p className="text-xs text-[var(--ink-2)] font-medium mt-1">
                                  @{txData.sender_twitter_handle} → @{txData.recipient_twitter_handle}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

            {/* ── Footer ── */}
            <div className="px-6 py-3 border-t border-[var(--border)] bg-[var(--bg)]">
              <div className="flex items-center justify-center gap-1.5 text-xs text-[var(--ink-2)] font-semibold">
                <IconShield />
                <span>{t('transacoes.secured')}</span>
                <span>🌸</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Transacoes;
