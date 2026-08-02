import { useEffect, useSyncExternalStore } from 'react';

import { getCachedSession, getSession, subscribeSession, type Session } from '@/lib/session';

/**
 * Sessão guardada do backend, lida do armazenamento seguro.
 *
 * Assina a fonte reativa de `lib/session` em vez de ler o storage por conta
 * própria. Quem grava é `signInAndStartSession` (`lib/auth.ts`), chamado pelo
 * botão de login — e é o aviso de `saveSession` que faz esta tela, e todas as
 * outras já montadas, sair do estado de convidado na hora. Lendo só na
 * montagem, como antes, a tela atrás do painel de perfil seguia mostrando
 * "No session yet" até o app reabrir.
 */
export function useSession(): { session: Session | null; hasSession: boolean; loading: boolean } {
  // O terceiro argumento é o snapshot de servidor: o app exporta
  // `web.output: "static"` (app.json), que pré-renderiza, e lá não há storage —
  // "ainda não lido" é a resposta certa nos dois lados.
  const cached = useSyncExternalStore(subscribeSession, getCachedSession, getCachedSession);

  // Primeira leitura do storage. `getSession` preenche o cache e avisa, então
  // uma vez por processo basta: as montagens seguintes já encontram o valor.
  useEffect(() => {
    if (cached === undefined) void getSession();
  }, [cached]);

  return {
    session: cached ?? null,
    hasSession: Boolean(cached),
    loading: cached === undefined,
  };
}
