import { useEffect, useState } from 'react';

import { getWallet } from '@/lib/session';
import { useWalletConnect } from '@/lib/walletconnect';

/**
 * O endereço de payout do usuário, de onde quer que ele venha.
 *
 * Duas fontes, e a ordem importa: uma sessão viva do WalletConnect manda sobre
 * o que está gravado, porque é a carteira que o usuário acabou de abrir. O
 * SecureStore é o que sobra quando o app reabre sem sessão de relay — quem
 * grava lá é o `WalletConnectProvider`, depois de vincular no backend.
 *
 * Existe para `ScreenShell` (que mostra o endereço no painel de perfil) e a
 * tela de Wallet (que consulta o saldo dele) não manterem duas cópias da mesma
 * regra.
 */
export function useWallet(): { address?: string; loading: boolean } {
  const [stored, setStored] = useState<string>();
  const [loading, setLoading] = useState(true);
  const wc = useWalletConnect();

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

  const connected = wc.isConnected ? wc.address : undefined;

  return { address: connected || stored, loading };
}
