import { useEffect, useState } from 'react';

import { getWallet } from '@/lib/session';
import { usePrivyWallet } from '@/lib/wallet';

/**
 * O endereço de payout do usuário, de onde quer que ele venha.
 *
 * Duas fontes, e a ordem importa: a carteira embutida viva do Privy manda
 * sobre o que está gravado, porque é a sessão atual. O SecureStore é o que
 * sobra quando o app reabre antes do Privy terminar de restaurar a sessão —
 * quem grava lá é o `WalletProvider` (`lib/wallet.tsx`), assim que a carteira
 * embutida existe.
 *
 * Existe para `ScreenShell` (que mostra o endereço no painel de perfil) e a
 * tela de Wallet (que consulta o saldo dele) não manterem duas cópias da mesma
 * regra.
 */
export function useWallet(): { address?: string; loading: boolean } {
  const [stored, setStored] = useState<string>();
  const [loading, setLoading] = useState(true);
  const wallet = usePrivyWallet();

  useEffect(() => {
    let cancelled = false;

    // Aplicado dentro do `then` de propósito: setState síncrono no corpo do
    // efeito é render em cascata para o React Compiler (mesmo acordo do
    // `use-session`).
    getWallet().then((next) => {
      if (cancelled) return;
      setStored(next?.address);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const connected = wallet.isConnected ? wallet.address : undefined;

  return { address: connected || stored, loading };
}
