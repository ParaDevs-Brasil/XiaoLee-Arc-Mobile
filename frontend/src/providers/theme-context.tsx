'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const STORAGE_KEY = 'xiaolee-theme'

// Tema escuro suspenso até ganhar uma variante da paleta neutra (pós-Lepton).
// Forçamos claro e ignoramos preferência salva/sistema para evitar UI quebrada.
function getInitialTheme(): Theme {
  return 'light'
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('light')

  useEffect(() => {
    const initial = getInitialTheme()
    setThemeState(initial)
    document.documentElement.classList.toggle('dark', initial === 'dark')
    localStorage.setItem(STORAGE_KEY, initial)
  }, [])

  function setTheme(next: Theme) {
    setThemeState(next)
    localStorage.setItem(STORAGE_KEY, next)
    document.documentElement.classList.toggle('dark', next === 'dark')
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider')
  return ctx
}
