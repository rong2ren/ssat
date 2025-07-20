'use client'

import { Header } from './Header'
import { AppStateProvider, usePreferences } from '@/contexts/AppStateContext'

interface LayoutWrapperProps {
  children: React.ReactNode
}

// Inner component that uses the context
function LayoutContent({ children }: LayoutWrapperProps) {
  const { showChinese, dispatch } = usePreferences()

  const handleLanguageToggle = () => {
    dispatch({ type: 'SET_SHOW_CHINESE', payload: !showChinese })
  }

  return (
    <>
      <Header 
        showChinese={showChinese}
        onLanguageToggle={handleLanguageToggle}
      />
      {children}
    </>
  )
}

// Main wrapper that provides the context
export function LayoutWrapper({ children }: LayoutWrapperProps) {
  return (
    <AppStateProvider>
      <LayoutContent>
        {children}
      </LayoutContent>
    </AppStateProvider>
  )
}