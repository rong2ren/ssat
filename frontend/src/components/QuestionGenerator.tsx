'use client'

import { useState } from 'react'
import { QuestionForm } from './QuestionForm'
import { QuestionDisplay } from './QuestionDisplay'
import { ProgressiveTestGenerator } from './ProgressiveTestGenerator'
import { Question, QuestionRequest } from '@/types/api'

interface QuestionGeneratorProps {
  showChinese: boolean
}

export default function QuestionGenerator({ showChinese }: QuestionGeneratorProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [isProgressiveMode, setIsProgressiveMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testRequest, setTestRequest] = useState<{
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[] // What user actually selected for display
  } | null>(null)

  // UI translations mapping
  const translations = {
    'Generate Questions': '生成题目',
    'Generating questions...': '正在生成题目...',
    'Error generating questions': '生成题目时出错'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleGenerateQuestions = async (request: QuestionRequest) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }

      const data = await response.json()
      setQuestions(data.questions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCompleteTest = (customConfig?: {
    sections: string[]
    counts: Record<string, number>
    difficulty: string
  }) => {
    if (customConfig) {
      // Use custom configuration - send individual sections to backend for better training
      setTestRequest({
        difficulty: customConfig.difficulty,
        include_sections: customConfig.sections, // Send original sections directly
        custom_counts: customConfig.counts,
        originalSelection: customConfig.sections
      })
    } else {
      // Use default configuration with separate analogy/synonym for better quality
      setTestRequest({
        difficulty: 'Medium',
        include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'],
        custom_counts: { quantitative: 10, analogy: 4, synonym: 6, reading: 7, writing: 1 }
      })
    }
    
    setIsProgressiveMode(true)
    setQuestions([]) // Clear individual questions
    setError(null)
  }

  // Show progressive test generator when in progressive mode
  if (isProgressiveMode && testRequest) {
    return (
      <ProgressiveTestGenerator 
        showChinese={showChinese}
        testRequest={testRequest}
        onBack={() => setIsProgressiveMode(false)}
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Question Generation Form */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">{t('Generate Questions')}</h2>
        <QuestionForm 
          onSubmit={handleGenerateQuestions}
          onGenerateCompleteTest={handleGenerateCompleteTest}
          loading={loading}
          showChinese={showChinese}
        />
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="text-red-600">
              <h3 className="font-medium">{t('Error generating questions')}</h3>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-blue-700">{t('Generating questions...')}</span>
          </div>
        </div>
      )}

      {/* Questions Display */}
      {questions.length > 0 && !loading && (
        <QuestionDisplay questions={questions} showChinese={showChinese} />
      )}
    </div>
  )
}