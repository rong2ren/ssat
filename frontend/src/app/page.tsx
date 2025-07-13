'use client'

import { useState } from 'react'
import QuestionGenerator from '@/components/QuestionGenerator'
import { Button } from '@/components/ui/Button'
import { Globe } from 'lucide-react'

export default function Home() {
  const [showChinese, setShowChinese] = useState(false)

  // UI translations mapping
  const translations = {
    'SSAT Practice Generator': 'SSAT 练习题生成器',
    'Generate high-quality SSAT questions for elementary students': '为小学生生成高质量的SSAT题目'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          {/* Language Toggle - Top Right but more visible */}
          <div className="flex justify-end mb-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowChinese(!showChinese)}
              className="flex items-center space-x-2"
            >
              <Globe className="h-4 w-4" />
              <span>{showChinese ? 'English' : '中文'}</span>
            </Button>
          </div>
          
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              {t('SSAT Practice Generator')}
            </h1>
            <p className="text-xl text-gray-600">
              {t('Generate high-quality SSAT questions for elementary students')}
            </p>
          </div>
        </div>
        
        <QuestionGenerator showChinese={showChinese} />
      </div>
    </main>
  )
}
