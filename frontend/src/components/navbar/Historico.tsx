import React, { useState, useEffect } from "react";
import UserData from "../UserData";
import { ChatMessage, HistoricoProps } from "@/interfaces";
import { useModal } from "@/hooks/useModal";

// ── SVG Icons ─────────────────────────────────────────────────────────────────
const IconBook = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
);
const IconRefresh = ({ spinning }: { spinning?: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={`w-4 h-4 ${spinning ? "animate-spin" : ""}`}>
    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
);
const IconClose = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconUser = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
);
const IconBot = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="15" x2="8" y2="17"/><line x1="16" y1="15" x2="16" y2="17"/>
  </svg>
);
const IconInbox = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-10 h-10">
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
  </svg>
);
const IconShield = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

// ── Helpers ───────────────────────────────────────────────────────────────────
function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

type FilterType = "all" | "user" | "assistant";

const FILTERS: { value: FilterType; label: string; Icon: () => React.ReactNode }[] = [
  { value: "all",       label: "All",      Icon: IconBook },
  { value: "user",      label: "You",      Icon: IconUser },
  { value: "assistant", label: "Xiaolee",  Icon: IconBot  },
];

// ── Component ─────────────────────────────────────────────────────────────────
const Historico: React.FC<HistoricoProps> = ({ shouldOpen = false, onClose }) => {
  const [filter, setFilter] = useState<FilterType>("all");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [refreshTick, setRefreshTick] = useState(0);
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);

  // Read chat history whenever modal opens or data refreshes
  useEffect(() => {
    if (!isOpen) return;
    const raw = UserData.getChatHistory();
    const msgs: ChatMessage[] = raw.flatMap(chat => [
      { content: chat.user_message.content,        role: "user"      as const, timestamp: chat.user_message.timestamp },
      { content: chat.assistant_response.content,  role: "assistant" as const, timestamp: chat.assistant_response.timestamp },
    ]).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    setHistory(msgs);
  }, [isOpen, refreshTick]);

  // Listen for new messages saved by ChatPanel
  useEffect(() => {
    const handler = () => setRefreshTick(t => t + 1);
    window.addEventListener('userDataLoaded', handler);
    return () => window.removeEventListener('userDataLoaded', handler);
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await UserData.fetchData();
    } catch { /* ignore */ } finally {
      setIsRefreshing(false);
      setRefreshTick(t => t + 1);
    }
  };

  const displayed = filter === "all" ? history : history.filter(m => m.role === filter);

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
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-6 pt-6 pb-4 border-b border-[var(--border)]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-[var(--accent)] flex items-center justify-center text-white shadow-e1">
                    <IconBook />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-[var(--ink)]">Chat History</h2>
                    <p className="text-sm text-[var(--ink-2)]">Your conversations with Xiaolee</p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="p-2 hover:bg-[var(--accent-soft)] rounded-xl transition-colors disabled:opacity-50 text-[var(--ink-3)] hover:text-[var(--accent)]"
                  >
                    <IconRefresh spinning={isRefreshing} />
                  </button>
                  <button
                    onClick={closeModal}
                    className="p-2 hover:bg-black/5 rounded-xl transition-colors text-[var(--ink-3)] hover:text-[var(--ink)]"
                  >
                    <IconClose />
                  </button>
                </div>
              </div>

              {/* Filter tabs */}
              <div className="flex gap-2">
                {FILTERS.map(({ value, label, Icon }) => (
                  <button
                    key={value}
                    onClick={() => setFilter(value)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                      filter === value
                        ? "bg-[var(--accent)] text-white shadow-e1"
                        : "bg-[var(--bg)] text-[var(--ink-2)] hover:bg-[var(--accent-soft)] border border-[var(--border)]"
                    }`}
                  >
                    <Icon />
                    {label}
                  </button>
                ))}
                <span className="ml-auto text-xs text-gray-400 self-center">
                  {displayed.length} msg{displayed.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {displayed.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="text-[var(--ink-3)] mb-4"><IconInbox /></div>
                  <h3 className="text-base font-bold text-[var(--ink-2)] mb-1">No messages yet</h3>
                  <p className="text-sm text-[var(--ink-3)] max-w-xs leading-relaxed">
                    Start chatting with Xiaolee to see your conversation history here.
                  </p>
                </div>
              ) : (
                displayed.map((msg, i) => {
                  const isUser = msg.role === "user";
                  return (
                    <div key={i} className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                      {/* Avatar */}
                      <div className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                        isUser
                          ? "bg-[var(--accent)] text-white"
                          : "bg-[var(--ink)] text-white"
                      }`}>
                        {isUser ? <IconUser /> : <IconBot />}
                      </div>

                      {/* Bubble */}
                      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-0.5`}>
                        <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                          isUser
                            ? "bg-[var(--accent)] text-white rounded-tr-sm"
                            : "bg-[var(--bg)] border border-[var(--border)] text-[var(--ink)] rounded-tl-sm"
                        }`}>
                          {msg.content}
                        </div>
                        <span className="text-[10px] text-gray-400 px-1">
                          {timeAgo(msg.timestamp)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-[var(--border)] bg-[var(--bg)]">
              <div className="flex items-center justify-center gap-1.5 text-xs text-[var(--ink-2)] font-medium">
                <span className="text-[var(--accent)]"><IconShield /></span>
                Secured by Xiaolee
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Historico;
