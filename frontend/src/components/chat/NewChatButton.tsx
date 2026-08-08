import React, { useEffect, useRef, useState } from "react";
import { IconEdit, IconClock } from "@/components/icons";
import { useChatSession } from "@/contexts/ChatSessionContext";
import { createChatSession } from "@/api/api";

/**
 * Botão único (não mais dividido) — abre um painel onde a escolha entre
 * "New chat" e reabrir uma conversa antiga é sempre explícita. Fundo
 * neutro/branco, não accent sólido: essa faixa é identidade da Xiaolee, não
 * um CTA, e rosa chapado ali chamava atenção demais. Mesma posição e mesmo
 * modelo do app mobile (`mobile/src/app/index.tsx::AssistantHeader`).
 */

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

export default function NewChatButton() {
  const { activeSessionId, setActiveSessionId, sessions, refreshSessions } = useChatSession();
  const [isOpen, setIsOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Fecha ao clicar fora — este componente não vive mais perto do listener
  // compartilhado da Navbar, então precisa do próprio (mesmo padrão dos
  // outros dropdowns: mousedown, só enquanto aberto).
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleNewChat = async () => {
    if (creating) return;
    setIsOpen(false);
    setCreating(true);
    try {
      const session = await createChatSession();
      setActiveSessionId(session.id);
      await refreshSessions();
    } catch (err) {
      console.error("Error creating chat session:", err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div ref={rootRef} className="relative shrink-0">
      <button
        onClick={() => setIsOpen((v) => !v)}
        title="New chat"
        className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-white px-2.5 py-1.5 text-[11px] font-bold text-gray-800 hover:bg-black/5 transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.3)]"
      >
        <IconEdit className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">New chat</span>
      </button>

      {isOpen && (
        <div className="absolute z-50 right-0 top-full mt-2 w-56 md:w-64 origin-top-right rounded-2xl bg-white border border-[var(--border)] shadow-e3 overflow-hidden">
          <button
            onClick={handleNewChat}
            disabled={creating}
            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-left hover:bg-black/5 transition-colors duration-150 disabled:opacity-60 border-b border-[var(--border)]"
          >
            <div className="w-7 h-7 shrink-0 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
              <IconEdit className="w-3.5 h-3.5" />
            </div>
            <span className="flex-1 text-sm font-bold text-gray-800">New chat</span>
          </button>

          {sessions.length === 0 ? (
            <div className="px-4 py-4 text-sm text-[var(--text-secondary)]">
              No conversations yet
            </div>
          ) : (
            <div className="max-h-72 overflow-y-auto custom-scrollbar">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => {
                    setActiveSessionId(session.id);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left hover:bg-black/5 transition-colors duration-150 ${
                    session.id === activeSessionId ? 'bg-[var(--accent-soft)]' : ''
                  }`}
                >
                  <div className="w-7 h-7 shrink-0 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
                    <IconClock className="w-3.5 h-3.5" />
                  </div>
                  <span className="flex-1 min-w-0 truncate text-sm font-medium text-[var(--text-primary)]">
                    {session.title}
                  </span>
                  <span className="shrink-0 text-[10px] text-[var(--text-secondary)]">
                    {timeAgo(session.updated_at)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
