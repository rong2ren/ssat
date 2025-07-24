'use client'

import { HomePage } from '@/components/HomePage'
import { usePreferences } from '@/contexts/AppStateContext'

export default function Home() {
  const { showChinese } = usePreferences()
  
  return (
    <HomePage showChinese={showChinese} />
  )
}
