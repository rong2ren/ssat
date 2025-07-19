'use client'

import { useState } from 'react'
import { QuestionDisplay } from './QuestionDisplay'
import { ProgressiveTestGenerator } from './ProgressiveTestGenerator'
import { PracticeQuestionsForm } from './forms/PracticeQuestionsForm'
import { CompleteTestForm } from './forms/CompleteTestForm'
import { Tabs, TabContent } from './ui/Tabs'
import { Question, QuestionRequest, ReadingPassage } from '@/types/api'

interface QuestionGeneratorProps {
  showChinese?: boolean
}

export default function QuestionGenerator({ showChinese = false }: QuestionGeneratorProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [passages, setPassages] = useState<ReadingPassage[]>([])
  const [contentType, setContentType] = useState<'questions' | 'passages' | 'prompts'>('questions')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeMode, setActiveMode] = useState('practice')
  const [testRequest, setTestRequest] = useState<{
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[] // What user actually selected for display
  } | null>(null)
  const [showCompleteTest, setShowCompleteTest] = useState(false)

  // UI translations mapping
  const translations = {
    'Custom Practice': '自定义练习',
    'Complete Test': '完整测试',
    'Generate 1-20 individual questions for targeted practice and skill building': '生成1-20道同类型练习题目，进行针对性训练',
    'Generate a comprehensive SSAT practice test with multiple sections': '生成完整的SSAT模拟考试测试',
    'Generating questions...': '正在生成题目...',
    'Error generating questions': '生成题目时出错',
    'Generate Another Test': '生成另一个测试'
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
      
      // Handle different response types based on content type
      if (data.questions) {
        // Standalone questions (math, verbal, analogy, synonym)
        setQuestions(data.questions)
        setPassages([])
        setContentType('questions')
      } else if (data.passages) {
        // Reading comprehension - keep passages in their natural structure
        setPassages(data.passages)
        setQuestions([])
        setContentType('passages')
      } else if (data.prompts) {
        // Writing prompts - convert to question-like format for display
        const promptQuestions = data.prompts.map((prompt: any, index: number) => ({
          id: `writing-${index}`,
          question_type: 'writing',
          difficulty: request.difficulty,
          text: prompt.prompt_text, // Just the prompt, not combined with instructions
          options: [], // No options for writing
          correct_answer: '',
          explanation: 'This is a creative writing task. Write a story with a beginning, middle, and end.',
          cognitive_level: 'CREATE',
          tags: ['writing', 'creative'],
          visual_description: prompt.visual_description || undefined,
          metadata: {
            isWritingPrompt: true,
            instructions: prompt.instructions
          }
        }))
        setQuestions(promptQuestions)
        setPassages([])
        setContentType('prompts')
      } else {
        throw new Error('Unknown response format')
      }
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
    let newTestRequest
    if (customConfig) {
      // Use custom configuration - send individual sections to backend for better training
      newTestRequest = {
        difficulty: customConfig.difficulty,
        include_sections: customConfig.sections, // Send original sections directly
        custom_counts: customConfig.counts,
        originalSelection: customConfig.sections
      }
    } else {
      // Use official SSAT Elementary format
      newTestRequest = {
        difficulty: 'Medium',
        include_sections: ['quantitative', 'verbal', 'reading', 'writing'],
        custom_counts: { quantitative: 30, verbal: 30, reading: 28, writing: 1 }
      }
    }
    
    setTestRequest(newTestRequest)
    
    // Stay on the same page but show complete test generator
    setShowCompleteTest(true)
    setQuestions([]) // Clear individual questions
    setPassages([]) // Clear passages
    setError(null)
  }

  const handleBackToForms = () => {
    setShowCompleteTest(false)
    setTestRequest(null)
  }

  const handleTabChange = (tabId: string) => {
    setActiveMode(tabId)
    // Don't clear test state when switching tabs - preserve it for later viewing
  }

  const tabs = [
    {
      id: 'practice',
      label: t('Custom Practice'),
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
          onTabChange={handleTabChange}
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
          {!showCompleteTest && (
            <CompleteTestForm
              onSubmit={handleGenerateCompleteTest}
              loading={loading}
              showChinese={showChinese}
            />
          )}
        </TabContent>
      </div>

      {/* Progressive Test Generator - rendered outside tabs to persist across tab switches */}
      {showCompleteTest && testRequest && (
        <div style={{ display: activeMode === 'complete' ? 'block' : 'none' }}>
          <ProgressiveTestGenerator 
            showChinese={showChinese}
            testRequest={testRequest}
            onBack={handleBackToForms}
          />
        </div>
      )}

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
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="relative mb-6">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
              <div className="absolute inset-0 rounded-full bg-blue-100 opacity-20"></div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {t('Generating questions...')}
            </h3>
            <p className="text-gray-600 max-w-md">
              Our AI is creating personalized SSAT questions based on your requirements. This may take a few moments.
            </p>
            <div className="mt-6 flex items-center space-x-2 text-sm text-gray-500">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
              <span>Processing...</span>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {activeMode === 'practice' && !loading && (
        <>
          {contentType === 'questions' && questions.length > 0 && (
            <QuestionDisplay questions={questions} showChinese={showChinese} />
          )}
          {contentType === 'passages' && passages.length > 0 && (
            <QuestionDisplay passages={passages} showChinese={showChinese} />
          )}
          {contentType === 'prompts' && questions.length > 0 && (
            <QuestionDisplay questions={questions} showChinese={showChinese} />
          )}
        </>
      )}

    </div>
  )
}