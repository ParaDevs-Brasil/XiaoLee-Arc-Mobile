import React from "react";
import Link from "next/link";
import { XiaoleeBubble } from "@/components/landing/primitives";
import { IconChat, IconSwap, IconGift, IconWallet, IconActivity } from "@/components/icons";

type EmptyStateProps = {
  onSuggestion: (text: string) => void;
};

const quickActions = [
  {
    icon: <IconGift size={18} />,
    title: "Create a campaign",
    subtitle: "Reward your community",
    href: "/campaigns",
  },
  {
    icon: <IconActivity size={18} />,
    title: "View dashboard",
    subtitle: "Metrics and activity",
    href: "/dashboard",
  },
  {
    icon: <IconSwap size={18} />,
    title: "Make a swap",
    subtitle: "Exchange tokens by chat",
    message: "I want to swap 10 USDC to EURC",
  },
  {
    icon: <IconWallet size={18} />,
    title: "Check balance",
    subtitle: "See your wallet funds",
    message: "What's my current balance?",
  },
] as const;

const suggestions = [
  "What can you do for me?",
  "How do campaigns work?",
  "Show my recent transactions",
];

export default function EmptyState({ onSuggestion }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-full px-4 py-6 msg-in">
      <div className="breath">
        <XiaoleeBubble size={72} />
      </div>

      <h3 className="mt-4 text-base md:text-lg font-bold text-gray-800">
        Hi! I&apos;m Xiaolee ✨
      </h3>
      <p className="mt-1 text-sm text-gray-600 max-w-sm text-center leading-relaxed">
        Swaps, campaigns and payments — all by message. What would you like to do?
      </p>

      {/* Quick actions */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-md">
        {quickActions.map((action) =>
          "href" in action ? (
            <Link
              key={action.title}
              href={action.href}
              className="suggestion-card flex items-center gap-3 px-4 py-3 rounded-xl border border-[var(--border)] bg-white shadow-e1 text-left"
            >
              <span className="shrink-0 w-9 h-9 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
                {action.icon}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-gray-800">{action.title}</span>
                <span className="block text-xs text-gray-500 truncate">{action.subtitle}</span>
              </span>
            </Link>
          ) : (
            <button
              key={action.title}
              onClick={() => onSuggestion(action.message)}
              className="suggestion-card flex items-center gap-3 px-4 py-3 rounded-xl border border-[var(--border)] bg-white shadow-e1 text-left cursor-pointer"
            >
              <span className="shrink-0 w-9 h-9 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
                {action.icon}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-gray-800">{action.title}</span>
                <span className="block text-xs text-gray-500 truncate">{action.subtitle}</span>
              </span>
            </button>
          )
        )}
      </div>

      {/* Suggested questions */}
      <div className="mt-5 flex flex-wrap items-center justify-center gap-2 max-w-md">
        {suggestions.map((text) => (
          <button
            key={text}
            onClick={() => onSuggestion(text)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[var(--border)] bg-white text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] hover:border-[rgba(216,27,120,0.25)] transition-colors cursor-pointer"
          >
            <IconChat size={12} />
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
