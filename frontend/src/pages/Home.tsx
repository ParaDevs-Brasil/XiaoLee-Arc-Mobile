import React from 'react';
import AnimePanel from '../components/AnimePanel';
import ChatPanel from '../components/ChatPanel';

export default function Home() {
  return (
    <div className="absolute inset-0 flex flex-col">
      <main className="flex-1 w-full relative z-10 overflow-hidden min-h-0">
        <div className="h-full w-full p-3 sm:p-4 md:p-8 lg:px-14 lg:py-10 xl:px-20 flex flex-col lg:grid lg:grid-cols-10 gap-3 md:gap-5 lg:gap-6 overflow-hidden">
          <AnimePanel />
          <ChatPanel />
        </div>
      </main>
    </div>
  );
}
