"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { listChatSessions, type ChatSessionSummary } from "@/api/api";

interface ChatSessionContextValue {
  activeSessionId: number | null;
  setActiveSessionId: (id: number | null) => void;
  sessions: ChatSessionSummary[];
  refreshSessions: () => Promise<void>;
}

const ChatSessionContext = createContext<ChatSessionContextValue>({
  activeSessionId: null,
  setActiveSessionId: () => {},
  sessions: [],
  refreshSessions: async () => {},
});

export function ChatSessionProvider({ children }: { children: React.ReactNode }) {
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await listChatSessions());
    } catch {
      // sem sessão de usuário ainda (ex: backend fora do ar) — dropdown fica vazio
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  return (
    <ChatSessionContext.Provider value={{ activeSessionId, setActiveSessionId, sessions, refreshSessions }}>
      {children}
    </ChatSessionContext.Provider>
  );
}

export const useChatSession = () => useContext(ChatSessionContext);
