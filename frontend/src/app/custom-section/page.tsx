'use client'

import { useState } from 'react'
import { QuestionDisplay } from '@/components/QuestionDisplay'
import { PracticeQuestionsForm } from '@/components/forms/PracticeQuestionsForm'
import { QuestionRequest } from '@/types/api'
import { useCustomSectionState, useCustomSectionActions, usePreferences } from '@/contexts/AppStateContext'
import { useAuth } from '@/contexts/AuthContext'
import AuthGuard from '@/components/auth/AuthGuard'
import { getAuthHeaders } from '@/utils/auth'
import { invalidateLimitsCache } from '@/components/DailyLimitsDisplay'

export default function CustomSectionPage() {
  const { user } = useAuth()
  // Use global state instead of local state
  const { questions, passages, contentType, loading, error } = useCustomSectionState()
  const { setLoading, setError, setQuestions, setPassages } = useCustomSectionActions()
  const { showChinese } = usePreferences()
  const [limitErrorInfo, setLimitErrorInfo] = useState<any>(null)

  // UI translations
  const translations = {
    'Custom Section Practice': '单项自定义练习',
    'Generate targeted practice questions for specific SSAT sections': '针对单项SSAT科目，生成个性化练习题',
    'Error generating questions': '生成题目时出错',
    'Generating questions...': '正在生成题目...',
    'Our AI is creating SSAT questions based on your requirements. This may take a few moments.': '我们的AI正在根据您的要求创建SSAT题目，请稍候片刻。',
    'Processing...': '处理中...',
    'Daily limit exceeded': '已达到每日限制',
    'You have reached your daily limit for this content type. Please try again tomorrow or check your usage in your profile.': '您已达到此题型的每日限制。请明天再试。',
    'Tip: Check your daily usage in your profile dropdown to see your current limits.': '💡 提示：在您的个人资料下拉菜单中可以查看您的当前使用情况。',
    'Current Usage:': '今日题型使用情况：',
    'Math': '数学',
    'Analogy': '类比',
    'Synonyms': '同义词',
    'Reading': '阅读',
    'Writing': '写作'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleGenerateQuestions = async (request: QuestionRequest) => {
    setLoading(true)
    setError(null)
    
    console.log('🔍 DAILY LIMITS: Starting generation for request:', request)
    
    try {
      // Get auth headers
      const headers = await getAuthHeaders()
      
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        
        if (errorData.error) {
          // Create a custom error with the message and additional data
          const error = new Error(errorData.error)
          ;(error as any).limitExceeded = errorData.limit_exceeded
          ;(error as any).limitsInfo = errorData.limits_info
          throw error
        } else {
          throw new Error(`Error: ${response.status}`)
        }
      }

      const data = await response.json()
      
      console.log('🔍 DAILY LIMITS: ✅ Generation completed successfully for:', request.question_type)
      
      // Invalidate limits cache to refresh the display
      if (user?.id) {
        invalidateLimitsCache(user.id)
        console.log('🔍 DAILY LIMITS: Invalidated cache after generation')
      }
      
      // Handle different response types based on content type
      if (data.questions) {
        // Standalone questions (math, verbal, analogy, synonym)
        console.log('🔍 DAILY LIMITS: Received questions:', data.questions.length)
        setQuestions(data.questions, 'questions', request)
      } else if (data.passages) {
        // Reading comprehension - keep passages in their natural structure
        console.log('🔍 DAILY LIMITS: Received passages:', data.passages.length)
        setPassages(data.passages, request)
      } else if (data.prompts) {
        // Writing prompts - convert to question-like format for display
        console.log('🔍 DAILY LIMITS: Received writing prompts:', data.prompts.length)
        const promptQuestions = data.prompts.map((prompt: { prompt_text: string; visual_description?: string; instructions: string }, index: number) => ({
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
        setQuestions(promptQuestions, 'prompts', request)
      } else {
        throw new Error('Invalid response format')
      }
      
    } catch (err) {
      console.error('🔍 DAILY LIMITS: ❌ Failed to generate questions:', err)
      
      // Handle limit exceeded errors specially
      if (err instanceof Error && (err as any).limitExceeded) {
        setError(err.message)
        setLimitErrorInfo((err as any).limitsInfo)
      } else if (err instanceof Error && err.message.includes('Daily limit exceeded')) {
        setError('You have reached your daily limit for this content type. Please try again tomorrow or check your usage in your profile.')
        setLimitErrorInfo(null)
      } else if (err instanceof Error && err.message.includes("You've reached your daily limit")) {
        setError(err.message)
        setLimitErrorInfo(null)
      } else {
        setError(err instanceof Error ? err.message : 'Unknown error occurred')
        setLimitErrorInfo(null)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-12">
        {/* Page Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {t('Custom Section Practice')}
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            {t('Generate targeted practice questions for specific SSAT sections')}
          </p>
        </div>

        <div className="max-w-6xl mx-auto space-y-8">
          {/* Practice Questions Form */}
          <PracticeQuestionsForm
            onSubmit={handleGenerateQuestions}
            loading={loading}
            showChinese={showChinese}
          />

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <div className="flex items-center">
                <div className="text-red-600 font-medium">
                  {error.includes('daily limit') ? t('Daily limit exceeded') : t('Error generating questions')}
                </div>
              </div>
              <p className="text-red-700 mt-2">{error}</p>
              {error.includes('daily limit') && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-blue-800 text-sm">
                    {t('Tip: Check your daily usage in your profile dropdown to see your current limits.')}
                  </p>
                  {limitErrorInfo && (
                    <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <p className="text-gray-700 text-sm font-medium mb-2">{t('Current Usage:')}</p>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div>{t('Math')}: {limitErrorInfo.usage.quantitative_generated}/{limitErrorInfo.limits.quantitative}</div>
                        <div>{t('Analogy')}: {limitErrorInfo.usage.analogy_generated}/{limitErrorInfo.limits.analogy}</div>
                        <div>{t('Synonyms')}: {limitErrorInfo.usage.synonyms_generated}/{limitErrorInfo.limits.synonyms}</div>
                        <div>{t('Reading')}: {limitErrorInfo.usage.reading_passages_generated}/{limitErrorInfo.limits.reading_passages}</div>
                        <div>{t('Writing')}: {limitErrorInfo.usage.writing_generated}/{limitErrorInfo.limits.writing}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
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
                  {t('Our AI is creating SSAT questions based on your requirements. This may take a few moments.')}
                </p>
                <div className="mt-6 flex items-center space-x-2 text-sm text-gray-500">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span>{t('Processing...')}</span>
                </div>
              </div>
            </div>
          )}

          {/* Results Display */}
          {!loading && (
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
      </div>
    </div>
    </AuthGuard>
  )
}