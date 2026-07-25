import React, { useState, useEffect } from 'react';
import Pfp from './Pfp';
import Video from './Video';
import UserData from './UserData';
import { IconStar } from '@/components/icons';

export default function AnimePanel() {
  const [currentPfp, setCurrentPfp] = useState(Video.getPfp());
  const [shouldLoop, setShouldLoop] = useState(false);
  const [chatCount, setChatCount] = useState(0);

  useEffect(() => {
    const loadChatCount = () => setChatCount(UserData.getChatHistory().length);
    loadChatCount();
    window.addEventListener('userDataLoaded', loadChatCount);
    return () => window.removeEventListener('userDataLoaded', loadChatCount);
  }, []);

  useEffect(() => {
    Video.setPfp("xiaolee_hello.mov");

    const unsubscribe = Video.subscribe((newPfp, loop) => {
      setCurrentPfp(newPfp);
      setShouldLoop(loop);
    });

    return () => {
      unsubscribe();
      Video.stopIdleRotation();
    };
  }, []);

  return (
    // Desktop only — below lg the live avatar lives inside the chat header (MiniAvatar)
    <div className="hidden lg:flex w-full lg:col-span-3 h-full min-h-0 rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-e2 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] shrink-0">
        <div>
          <h3 className="text-sm font-bold text-grad">Xiaolee</h3>
          <p className="text-xs text-gray-500 mt-0.5">Your DeFi companion</p>
        </div>
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-[var(--success)] bg-emerald-50 border border-emerald-100 rounded-lg px-2 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
          Online
        </span>
      </div>

      {/* Avatar — locked to the source video aspect (~480x650) so the full
          upper body is always in frame; sized by available height, centered */}
      <div className="flex-1 min-h-0 p-3 flex items-center justify-center">
        <div className="breath relative h-full max-w-full aspect-[48/65] rounded-2xl overflow-hidden border border-[var(--border)] bg-[var(--accent-soft)] shadow-e1">
          <Pfp pfp={currentPfp} loop={shouldLoop} objectPosition="50% 0%" />
        </div>
      </div>

      {/* Character info */}
      <div className="px-4 py-3 border-t border-[var(--border)] shrink-0 space-y-2">
        <p className="text-xs text-gray-600 leading-relaxed">
          Always ready to help with swaps, campaigns and payments.
        </p>
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-gray-500">
            {chatCount > 0 ? `${chatCount} conversation${chatCount === 1 ? '' : 's'}` : 'New here? Say hi!'}
          </span>
          <span className="flex items-center gap-0.5 text-amber-400" aria-label="5 star assistant">
            {Array.from({ length: 5 }).map((_, i) => (
              <IconStar key={i} size={11} />
            ))}
          </span>
        </div>
      </div>
    </div>
  );
}
