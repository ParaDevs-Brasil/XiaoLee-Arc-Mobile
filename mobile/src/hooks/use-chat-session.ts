import { useSyncExternalStore } from 'react';

import type { ChatSessionSummary } from '@/api/backend';
import {
  getActiveChatSessionId,
  getChatSessions,
  subscribeChatSessions,
} from '@/lib/chat-session';

/**
 * Sessão de chat ativa + lista de sessões, lidas da fonte reativa em
 * `lib/chat-session.ts`. Mesmo padrão de `use-session.ts`, sem o passo de
 * "primeira leitura do storage" — aqui não há storage, o cache já nasce certo.
 */
export function useChatSession(): {
  activeChatSessionId: number | null;
  sessions: ChatSessionSummary[];
} {
  const activeChatSessionId = useSyncExternalStore(
    subscribeChatSessions,
    getActiveChatSessionId,
    getActiveChatSessionId,
  );
  const sessions = useSyncExternalStore(subscribeChatSessions, getChatSessions, getChatSessions);

  return { activeChatSessionId, sessions };
}
