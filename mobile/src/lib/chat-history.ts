import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Histórico de chat, persistido no aparelho.
 *
 * O backend nunca preenche `chat_history` no dossiê do usuário — devolve lista
 * vazia fixa (`campaigns_routes.py:557`), e não é bug: nada no backend grava
 * conversa em lugar nenhum. O web sabe disso e resolve do lado do cliente,
 * gravando cada troca no `localStorage` assim que ela acontece
 * (`UserData.addLocalChatMessage`, chamada em `ChatPanel.tsx` tanto na
 * resposta quanto no erro) — é dali, e não do backend, que a tela de
 * Histórico do web lê. Este módulo é o mesmo acordo, com `AsyncStorage` no
 * lugar do `localStorage`.
 *
 * Sem escopo por usuário, de propósito: a sessão ainda não está ligada a
 * nenhuma tela (`use-session.ts`), então hoje só existe conversa anônima — e
 * é o que o web também faz, guardando numa chave só, independente de quem
 * está autenticado.
 */

const KEY = 'xiaolee_chat_history';

/**
 * ~200 trocas, o mesmo teto do web (`UserData.tsx:342`) — só que contado em
 * mensagens, porque aqui não existe o objeto de par que o web usa para cortar
 * a lista.
 */
const MAX_MESSAGES = 400;

export interface StoredMessage {
  role: 'user' | 'assistant';
  content: string;
  /** ISO 8601, capturado no instante do envio ou da resposta — não é a hora de exibição. */
  at: string;
}

/**
 * Lê o histórico salvo, do mais antigo para o mais novo — a mesma ordem em
 * que `appendChatMessage` grava, então quem lê não precisa ordenar de novo.
 *
 * Nunca lança: armazenamento corrompido ou indisponível vira lista vazia, que
 * é o estado "nada aqui ainda" — mais seguro que derrubar a tela por um JSON
 * que não devia ter sobrevivido a uma atualização do app.
 */
export async function loadChatHistory(): Promise<StoredMessage[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Grava uma mensagem no fim do histórico.
 *
 * Chamada duas vezes por troca — uma para a mensagem do usuário, outra para a
 * resposta —, e não uma vez com o par pronto: no chat as duas nascem em
 * momentos diferentes (a resposta depende de uma chamada de rede), e carimbar
 * as duas com o mesmo instante perderia o tempo real de cada uma.
 *
 * Nunca lança: se o `AsyncStorage` falhar (sem espaço, indisponível), a
 * mensagem já está na tela — perder só a gravação não deve travar o chat.
 */
export async function appendChatMessage(role: StoredMessage['role'], content: string): Promise<void> {
  const current = await loadChatHistory();
  const next: StoredMessage[] = [...current, { role, content, at: new Date().toISOString() }].slice(
    -MAX_MESSAGES,
  );

  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // sem espaço ou storage indisponível — nada a fazer daqui
  }
}

/**
 * Apaga o histórico. Chamada por `signOutEverywhere` (`lib/auth.ts`) — hoje
 * inerte, porque nenhuma tela ainda dispara login, mas no dia em que uma
 * disparar o comportamento já está certo: sair também esquece a conversa,
 * como no web.
 */
export async function clearChatHistory(): Promise<void> {
  try {
    await AsyncStorage.removeItem(KEY);
  } catch {
    // nada a limpar
  }
}
