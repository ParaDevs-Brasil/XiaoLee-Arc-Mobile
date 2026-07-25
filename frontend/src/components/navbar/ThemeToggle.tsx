'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/providers/theme-context'
import { SunIcon, MoonIcon } from '@heroicons/react/24/solid'

export const ThemeToggle = () => {
  const [mounted, setMounted] = useState(false)
  const { theme, setTheme } = useTheme()

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-1.5 sm:p-2 sm:mx-2 hover:scale-120 cursor-pointer transition-all duration-300 easy-in-out rounded-full text-[var(--text-primary)] shrink-0"
      aria-label="Toggle Dark Mode"
    >
      {theme === 'dark' ? (
        <SunIcon className="w-5 h-5 sm:w-6 sm:h-6 text-[var(--text-primary)]" />
      ) : (
        <MoonIcon className="w-5 h-5 sm:w-6 sm:h-6 text-[var(--text-primary)]" />
      )}
    </button>
  )
} 