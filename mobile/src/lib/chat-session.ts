import { listChatSessions, type ChatSessionSummary } from '@/api/backend';

/**
 * Sessão de chat ativa — fonte única e reativa, mesmo idioma de `lib/session.ts`
 * (cache + `Set<Listener>` + `useSyncExternalStore`), mas sem storage: ao
 * contrário da identidade da carteira, a conversa ativa não precisa sobreviver
 * a um restart do app (o web também reseta ao recarregar a página).
 */

type Listener = () => void;
const listeners = new Set<Listener>();

let activeId: number | null = null;
let sessions: ChatSessionSummary[] = [];

function emit(): void {
  for (const listener of listeners) listener();
}

export function subscribeChatSessions(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getActiveChatSessionId(): number | null {
  return activeId;
}

export function setActiveChatSessionId(id: number | null): void {
  activeId = id;
  emit();
}

export function getChatSessions(): ChatSessionSummary[] {
  return sessions;
}

export async function refreshChatSessions(): Promise<void> {
  try {
    sessions = await listChatSessions();
  } catch {
    // sem sessão de usuário ainda (ex: backend fora do ar) — painel fica vazio
    return;
  }
  emit();
}
