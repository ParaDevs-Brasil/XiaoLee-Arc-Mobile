import { useEffect, useState } from 'react';

import { getSession, type Session } from '@/lib/session';

/**
 * Sessão guardada do backend, lida do armazenamento seguro.
 *
 * Hoje devolve sempre `null`: quem grava é `signInAndStartSession`
 * (`lib/auth.ts`), que ainda não é chamado por nenhuma tela. Mesmo assim as
 * telas leem daqui em vez de um `false` fixo — no dia em que o login for
 * ligado, elas passam a ver a sessão sem precisar de mais nenhuma alteração.
 */
export function useSession(): { session: Session | null; hasSession: boolean; loading: boolean } {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    // O resultado só é aplicado dentro do `then`: setState síncrono no corpo
    // do efeito é render em cascata para o React Compiler.
    getSession().then((next) => {
      if (cancelled) return;
      setSession(next);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return { session, hasSession: session !== null, loading };
}
