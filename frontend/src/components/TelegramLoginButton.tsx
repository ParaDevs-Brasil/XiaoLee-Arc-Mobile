"use client";
import { useEffect, useRef, useCallback } from "react";
import api from "@/api/api";
import UserData from "@/components/UserData";

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

interface Props {
  onSuccess?: () => void;
  onError?: (err: unknown) => void;
}

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramUser) => void;
  }
}

export default function TelegramLoginButton({ onSuccess, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const botName = process.env.NEXT_PUBLIC_TELEGRAM_BOT_NAME;

  const handleAuth = useCallback(
    async (tgUser: TelegramUser) => {
      try {
        const { data } = await api.post("/auth/telegram/login", tgUser);
        const { session_id, twitter_user_id, username, custodial_wallet_address } = data;

        UserData.setSessionId(session_id);
        UserData.setTwitterUserId(twitter_user_id);

        if (typeof window !== "undefined") {
          window.localStorage.setItem("xiaolee_devnet_session", session_id);
        }

        // Set user_info directly so the navbar updates immediately
        UserData.setUserData({
          user_info: {
            twitter_user_id,
            twitter_handle: username,
            created_at: new Date().toISOString(),
            custodial_wallet_address: custodial_wallet_address ?? undefined,
          },
          balances: [],
          history: { chat_history: [], swaps: [], transactions: [] },
          campaigns: [],
          session_id,
        });

        onSuccess?.();
      } catch (err) {
        console.error("Telegram login failed:", err);
        onError?.(err);
      }
    },
    [onSuccess, onError]
  );

  useEffect(() => {
    if (!botName || !containerRef.current) return;

    window.onTelegramAuth = handleAuth;

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", botName);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    script.async = true;
    containerRef.current.appendChild(script);

    return () => {
      delete window.onTelegramAuth;
    };
  }, [botName, handleAuth]);

  if (!botName) {
    return (
      <div className="text-xs text-red-400 px-2">
        NEXT_PUBLIC_TELEGRAM_BOT_NAME not set
      </div>
    );
  }

  return <div ref={containerRef} />;
}
