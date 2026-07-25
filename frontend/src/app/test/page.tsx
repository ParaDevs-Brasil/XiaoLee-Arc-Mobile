"use client";
import React from 'react';
import { ThemeProviderWrapper } from '../../providers/ThemeProvider';
import Navbar from '../../components/navbar/Navbar';
import TestComponents from '../../views/TestComponents';

export default function TestPage() {
  return (
    <ThemeProviderWrapper>
      <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-100">
        <Navbar />
        <TestComponents />
      </div>
    </ThemeProviderWrapper>
  );
}
