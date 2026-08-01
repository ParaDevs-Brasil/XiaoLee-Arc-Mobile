import { useEffect, useState } from 'react';

import { getSession, type Session } from '@/lib/session';

/**
 * Sessão guardada do backend, lida do armazenamento seguro.
 *
 * Quem grava é `signInAndStartSession` (`lib/auth.ts`), chamado pelo botão de
 * login do `ProfileMenu` — que vive no `ScreenShell`, logo em todas as telas.
 * Lido na montagem porque a sessão sobrevive ao fechamento do app.
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
