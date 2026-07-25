import React from "react";
import { XiaoleeBubble } from "@/components/landing/primitives";
import { IconCheck } from "@/components/icons";
import MiniAvatar from "@/components/chat/MiniAvatar";

type ChatHeaderProps = {
  authenticated: boolean;
};

export default function ChatHeader({ authenticated }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-2 px-3 md:px-5 py-2.5 md:py-3 border-b border-[var(--border)] shrink-0 bg-white/60">
      <div className="flex items-center gap-2.5 md:gap-3 min-w-0">
        <div className="relative">
          {/* Below lg the AnimePanel is hidden, so the live avatar plays here */}
          <span className="lg:hidden">
            <MiniAvatar size={40} />
          </span>
          <span className="hidden lg:block">
            <XiaoleeBubble size={38} />
          </span>
          <span className="absolute -bottom-0.5 -right-0.5 z-10 w-3 h-3 rounded-full bg-[var(--success)] border-2 border-white" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-gray-800 leading-tight">Xiaolee</h2>
            <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-[var(--success)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
              Online
            </span>
          </div>
          <p className="text-xs text-gray-500 truncate">
            Your intelligent DeFi assistant
          </p>
        </div>
      </div>

      {authenticated && (
        <span
          className="flex items-center gap-1.5 shrink-0 text-[10px] font-bold uppercase tracking-widest text-[var(--success)] bg-emerald-50 border border-emerald-100 rounded-lg px-2 py-1"
          title="Authenticated"
        >
          <IconCheck size={10} sw={3} />
          <span className="hidden sm:inline">Authenticated</span>
        </span>
      )}
    </div>
  );
}
