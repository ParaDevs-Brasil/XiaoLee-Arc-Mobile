'use client'

import { ThemeProvider } from '@/providers/theme-context'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

interface ThemeProviderProps {
  children: React.ReactNode
}

export function ThemeProviderWrapper({ children }: ThemeProviderProps) {
  return (
    <ThemeProvider>
      {children}
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="colored"
      />
    </ThemeProvider>
  )
}