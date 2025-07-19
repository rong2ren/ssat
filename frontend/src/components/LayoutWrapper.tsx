'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { Header } from './Header'

interface LayoutWrapperProps {
  children: React.ReactNode
}

export function LayoutWrapper({ children }: LayoutWrapperProps) {
  const [showChinese, setShowChinese] = useState<boolean>(false)

  // Show header on all pages for consistent navigation
  return (
    <>
      <Header 
        showChinese={showChinese}
        onLanguageToggle={() => setShowChinese(!showChinese)}
      />
      {children}
    </>
  )
}