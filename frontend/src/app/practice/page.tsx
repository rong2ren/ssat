'use client'

import { useState } from 'react'
import QuestionGenerator from '@/components/QuestionGenerator'
import { Button } from '@/components/ui/Button'
import { Globe, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function PracticePage() {
  const [showChinese, setShowChinese] = useState<boolean>(false)

  // UI translations mapping
  const translations = {
    'SSAT Practice Generator': 'SSAT 练习题生成器',
    'Back to Home': '返回首页'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          {/* Navigation */}
          <div className="flex justify-between items-center mb-8">
            <Link href="/">
              <Button
                variant="ghost"
                size="sm"
                className="flex items-center space-x-2"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>{t('Back to Home')}</span>
              </Button>
            </Link>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowChinese(!showChinese)}
              className="flex items-center space-x-2 bg-white/80 backdrop-blur-sm border-white/50 hover:bg-white/90"
            >
              <Globe className="h-4 w-4" />
              <span>{showChinese ? 'English' : '中文'}</span>
            </Button>
          </div>
          
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-4 leading-tight">
              {t('SSAT Practice Generator')}
            </h1>
          </div>
        </div>
        
        <QuestionGenerator showChinese={showChinese} />
      </div>
    </main>
  )
}