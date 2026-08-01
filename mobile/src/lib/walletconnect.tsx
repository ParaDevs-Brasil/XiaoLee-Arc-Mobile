import '@walletconnect/react-native-compat';

import {
  useWalletConnectModal,
  WalletConnectModal,
} from '@walletconnect/modal-react-native';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { linkWallet } from '@/api/backend';
import { ApiError } from '@/api/client';
import { getWallet, saveWallet, type ConnectedWallet } from '@/lib/session';

/**
 * Provider de WalletConnect para o app mobile.
 *
 * Abre o modal nativo de seleção de carteira (Metamask, Rainbow, Trust, etc.)
 * e vincula o endereço conectado ao backend via POST /auth/wallet.
 */

const PROJECT_ID = process.env.EXPO_PUBLIC_WC_PROJECT_ID?.trim() || 'CHANGE_ME';
const RELAY_URL = 'wss://relay.walletconnect.com';

const APP_METADATA = {
  name: 'XiaoLee',
  description: 'XiaoLee - AI DeFi Assistant',
  url: 'https://xiaolee.ai',
  icons: ['https://xiaolee.ai/icon.png'],
  redirect: {
    native: 'xiaolee://',
    universal: 'https://xiaolee.ai',
  },
};

interface WalletConnectContextValue {
  isConnected: boolean;
  address: string | undefined;
  isLinking: boolean;
  linkError: string | null;
  openModal: () => void;
  disconnect: () => void;
}

const WCContext = createContext<WalletConnectContextValue | null>(null);

export function WalletConnectProvider({ children }: { children: ReactNode }) {
  const { isConnected, address, open, provider } = useWalletConnectModal();
  const [isLinking, setIsLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [storedWallet, setStoredWallet] = useState<ConnectedWallet | null>(null);

  // Restaura wallet do SecureStore na montagem
  useEffect(() => {
    getWallet().then(setStoredWallet);
  }, []);

  // Quando conecta via WalletConnect, vincula ao backend
  useEffect(() => {
    if (!isConnected || !address) return;
    if (storedWallet && storedWallet.address.toLowerCase() === address.toLowerCase()) return;

    setIsLinking(true);
    setLinkError(null);

    linkWallet(address, 'arc')
      .then((linked) => {
        const wallet = { address: linked.address, chain: linked.chain };
        return saveWallet(wallet).then(() => setStoredWallet(wallet));
      })
      .catch((err) => {
        setLinkError(err instanceof ApiError ? err.message : String(err));
      })
      .finally(() => setIsLinking(false));
  }, [isConnected, address]);

  const openModal = () => open();

  const disconnect = async () => {
    if (provider) {
      try {
        await provider.disconnect();
      } catch {
        // wallet pode já estar desconectada
      }
    }
  };

  const value = useMemo(
    () => ({
      isConnected,
      address,
      isLinking,
      linkError,
      openModal,
      disconnect,
    }),
    [isConnected, address, isLinking, linkError],
  );

  return (
    <WCContext.Provider value={value}>
      {children}
      <WalletConnectModal
        projectId={PROJECT_ID}
        providerMetadata={APP_METADATA}
        relayUrl={RELAY_URL}
        themeMode="light"
      />
    </WCContext.Provider>
  );
}

export function useWalletConnect(): WalletConnectContextValue {
  const ctx = useContext(WCContext);
  if (!ctx) {
    throw new Error('useWalletConnect deve ser usado dentro de WalletConnectProvider');
  }
  return ctx;
}
