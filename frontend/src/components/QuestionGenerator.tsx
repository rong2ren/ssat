'use client'

import { useState } from 'react'
import { QuestionForm } from './QuestionForm'
import { QuestionDisplay } from './QuestionDisplay'
import { TestDisplay } from './TestDisplay'
import { Question, QuestionRequest, TestSection } from '@/types/api'

interface QuestionGeneratorProps {
  showChinese: boolean
}

export default function QuestionGenerator({ showChinese }: QuestionGeneratorProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [testSections, setTestSections] = useState<TestSection[]>([])
  const [isCompleteTest, setIsCompleteTest] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      setIsCompleteTest(false)
      setTestSections([]) // Clear test sections
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCompleteTest = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/generate/complete-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          difficulty: 'Medium',
          include_sections: ['math', 'verbal', 'reading'],
          custom_counts: { math: 10, verbal: 10, reading: 3 }
        }),
      })

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }

      const data = await response.json()
      // Store sections for complete test display
      setTestSections(data.sections)
      setIsCompleteTest(true)
      setQuestions([]) // Clear individual questions
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
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
      {questions.length > 0 && !loading && !isCompleteTest && (
        <QuestionDisplay questions={questions} showChinese={showChinese} />
      )}
      
      {/* Complete Test Display */}
      {testSections.length > 0 && !loading && isCompleteTest && (
        <TestDisplay sections={testSections} showChinese={showChinese} />
      )}
    </div>
  )
}