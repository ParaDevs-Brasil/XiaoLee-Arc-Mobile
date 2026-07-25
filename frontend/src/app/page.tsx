"use client";
import React from 'react';
import Home from '../pages/Home';
import Navbar from '../components/navbar/Navbar';
import { ThemeProviderWrapper } from '@/providers/ThemeProvider';

export default function HomePage() {
  return (
    <ThemeProviderWrapper>
    <div className="h-[100dvh] w-full flex flex-col bg-[var(--main-bg)]">
      <Navbar />
      <div className="flex-1 w-full relative">
        <Home />
      </div>
    </div>
    </ThemeProviderWrapper>
  );
}