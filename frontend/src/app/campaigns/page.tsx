"use client";
import React from 'react';
import Navbar from '../../components/navbar/Navbar';
import CampanhasNew from '../../pages/CampanhasNew';
import { ThemeProviderWrapper } from '@/providers/ThemeProvider';

export default function CampaignsPage() {
  return (
    <ThemeProviderWrapper>
    <div className="min-h-screen bg-[var(--main-bg)]">
      <Navbar />
      <CampanhasNew />
    </div>
    </ThemeProviderWrapper>
  );
}