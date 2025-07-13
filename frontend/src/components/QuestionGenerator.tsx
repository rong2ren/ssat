'use client'

import { useState } from 'react'
import { QuestionDisplay } from './QuestionDisplay'
import { ProgressiveTestGenerator } from './ProgressiveTestGenerator'
import { PracticeQuestionsForm } from './forms/PracticeQuestionsForm'
import { CompleteTestForm } from './forms/CompleteTestForm'
import { Tabs, TabContent } from './ui/Tabs'
import { Question, QuestionRequest } from '@/types/api'

interface QuestionGeneratorProps {
  showChinese: boolean
}

export default function QuestionGenerator({ showChinese }: QuestionGeneratorProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [isProgressiveMode, setIsProgressiveMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeMode, setActiveMode] = useState('practice')
  const [testRequest, setTestRequest] = useState<{
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[] // What user actually selected for display
  } | null>(null)

  // UI translations mapping
  const translations = {
    'Practice Questions': '练习题目',
    'Complete Test': '完整测试',
    'Generate 1-20 individual questions for targeted practice and skill building': '生成1-20道个人题目，进行针对性练习和技能培养',
    'Generate a comprehensive SSAT practice test with multiple sections': '生成完整的SSAT模拟考试',
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

  const tabs = [
    {
      id: 'practice',
      label: t('Practice Questions'),
      icon: <span className="text-lg">🎯</span>,
      description: t('Generate 1-20 individual questions for targeted practice and skill building')
    },
    {
      id: 'complete',
      label: t('Complete Test'),
      icon: <span className="text-lg">📝</span>,
      description: t('Generate a comprehensive SSAT practice test with multiple sections')
    }
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Main Generator Interface */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        {/* Mode Selector Tabs */}
        <Tabs 
          tabs={tabs} 
          defaultTab="practice"
          onTabChange={setActiveMode}
        />

        {/* Practice Questions Form */}
        <TabContent activeTab={activeMode} tabId="practice">
          <PracticeQuestionsForm
            onSubmit={handleGenerateQuestions}
            loading={loading}
            showChinese={showChinese}
          />
        </TabContent>

        {/* Complete Test Form */}
        <TabContent activeTab={activeMode} tabId="complete">
          <CompleteTestForm
            onSubmit={handleGenerateCompleteTest}
            loading={loading}
            showChinese={showChinese}
          />
        </TabContent>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
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

      {/* Results Display */}
      {activeMode === 'practice' && questions.length > 0 && !loading && (
        <QuestionDisplay questions={questions} showChinese={showChinese} />
      )}
    </div>
  )
}