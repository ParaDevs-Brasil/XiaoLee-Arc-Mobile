"use client";
import { useState, useCallback } from "react";
import api from "@/api/api";
import UserData from "@/components/UserData";
import { setWeb3AuthProvider } from "@/lib/web3authProvider";

interface Props {
  onSuccess?: () => void;
  onError?: (err: unknown) => void;
}

export default function Web3AuthButton({ onSuccess, onError }: Props) {
  const [loading, setLoading] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_WEB3AUTH_CLIENT_ID;

  const handleLogin = useCallback(async () => {
    if (!clientId) {
      console.error("NEXT_PUBLIC_WEB3AUTH_CLIENT_ID not set");
      onError?.(new Error("Web3Auth client ID not configured"));
      return;
    }

    setLoading(true);
    try {
      const { CHAIN_NAMESPACES, WEB3AUTH_NETWORK } = await import("@web3auth/base");
      const { Web3Auth } = await import("@web3auth/modal");
      const { SolanaPrivateKeyProvider } = await import("@web3auth/solana-provider");

      const chainConfig = {
        chainNamespace: CHAIN_NAMESPACES.SOLANA,
        chainId: "0x3",
        rpcTarget: "https://api.devnet.solana.com",
        displayName: "Solana Devnet",
        blockExplorerUrl: "https://explorer.solana.com/?cluster=devnet",
        ticker: "SOL",
        tickerName: "Solana",
      };

      const privateKeyProvider = new SolanaPrivateKeyProvider({
        config: { chainConfig },
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const web3auth = new Web3Auth({
        clientId,
        web3AuthNetwork: WEB3AUTH_NETWORK.SAPPHIRE_DEVNET,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        privateKeyProvider: privateKeyProvider as any,
      });

      // v9 modal requires initModal() to set up the UI connectors
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (web3auth as any).initModal();

      // Clear stale cached session so the modal always starts fresh
      if (web3auth.status === "connected") {
        try { await web3auth.logout(); } catch { /* ignore */ }
      }

      await web3auth.connect();

      if (!web3auth.provider) {
        throw new Error("No provider after connect");
      }

      // Persist provider so Wallet.tsx can sign transactions without Phantom
      setWeb3AuthProvider(web3auth.provider);

      const web3UserInfo = await web3auth.getUserInfo();

      // Get Solana address: try public key method first (social login),
      // fall back to getAccounts (external wallets like Backpack)
      let address: string | undefined;
      try {
        const pubKey = await web3auth.provider.request({ method: "solanaPublicKey" });
        address = pubKey as string;
      } catch {
        const rawAccounts = await web3auth.provider.request({ method: "getAccounts" });
        const accounts = rawAccounts as string[];
        address = accounts?.[0];
      }

      const { data } = await api.post("/auth/google/login", {
        address,
        email: web3UserInfo.email ?? "",
        name: web3UserInfo.name ?? web3UserInfo.email ?? address.slice(0, 8),
      });

      const { session_id, twitter_user_id, username, custodial_wallet_address } = data;

      UserData.setSessionId(session_id);
      UserData.setTwitterUserId(twitter_user_id);

      if (typeof window !== "undefined") {
        window.localStorage.setItem("xiaolee_devnet_session", session_id);
      }

      const userInfo = {
        twitter_user_id,
        twitter_handle: username,
        created_at: new Date().toISOString(),
        custodial_wallet_address: custodial_wallet_address ?? address,
      };

      UserData.setUserData({
        user_info: userInfo,
        balances: [],
        history: { chat_history: [], swaps: [], transactions: [] },
        campaigns: [],
        session_id,
      });

      onSuccess?.();
    } catch (err) {
      console.error("Web3Auth login failed:", err);
      onError?.(err);
    } finally {
      setLoading(false);
    }
  }, [clientId, onSuccess, onError]);

  if (!clientId) {
    return (
      <div className="text-xs text-red-400 px-2">
        NEXT_PUBLIC_WEB3AUTH_CLIENT_ID not set
      </div>
    );
  }

  return (
    <button
      onClick={handleLogin}
      disabled={loading}
      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white text-sm font-semibold shadow hover:from-rose-600 hover:to-orange-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
    >
      <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
      {loading ? "Conectando..." : "Login com Google"}
    </button>
  );
}
