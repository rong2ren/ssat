'use client'

import { useState } from 'react'
import { ProgressiveTestGenerator } from '@/components/ProgressiveTestGenerator'
import { CompleteTestForm } from '@/components/forms/CompleteTestForm'
import { useFullTestState, useFullTestActions, usePreferences } from '@/contexts/AppStateContext'
import { getAuthHeaders } from '@/utils/auth'

export default function FullTestPage() {
  // Use global state for persistent data (testRequest, showCompleteTest, jobStatus)
  const { testRequest, showCompleteTest, jobStatus } = useFullTestState()
  const { setTestRequest, setShowCompleteTest, setJobStatus } = useFullTestActions()
  const { showChinese } = usePreferences()
  
  // Local state to store the job ID and preparation status
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [isPreparing, setIsPreparing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [limitErrorInfo, setLimitErrorInfo] = useState<any>(null)

  // UI translations
  const translations = {
    'Complete Practice Test': '完整模拟测试',
    'Generate comprehensive SSAT practice tests with multiple sections': '生成完整SSAT模拟测试题',
    'Daily limit exceeded': '已达到每日限制',
    'Go Back to Configure': '返回配置',
    'Current Usage:': '今日题型使用情况：',
    'Math': '数学',
    'Analogy': '类比',
    'Synonyms': '同义词',
    'Reading': '阅读',
    'Writing': '写作',
    'Tip: Check your daily usage in your profile dropdown to see your current limits.': '💡 提示：在您的个人资料下拉菜单中可以查看您的当前使用情况。'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

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
        originalSelection: customConfig.sections,
        is_official_format: false // Custom format
      }
      console.log('🔧 DEBUG: Using CUSTOM format:', newTestRequest)
    } else {
      // Use official SSAT Elementary format - separate verbal into analogy and synonym
      newTestRequest = {
        difficulty: 'Medium',
        include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'],
        custom_counts: { 
          quantitative: 30, 
          analogy: 12,  // 40% of 30 = 12 questions
          synonym: 18,  // 60% of 30 = 18 questions
          reading: 28, 
          writing: 1 
        },
        is_official_format: true // Official format
      }
      console.log('🎯 DEBUG: Using OFFICIAL format:', newTestRequest)
    }
    
    console.log('🔍 DAILY LIMITS: Starting complete test generation with sections:', newTestRequest.include_sections)
    
    setTestRequest(newTestRequest)
    
    // Show the progressive test generator
    setShowCompleteTest(true)
    // Clear any existing job status to ensure fresh start
    setJobStatus(null)
    setCurrentJobId(null)
    
    // Show preparation state immediately
    setIsPreparing(true)
    
    // Start generation immediately
    startGeneration(newTestRequest)
  }

  const startGeneration = async (testRequest: any) => {
    setError(null) // Clear any previous errors
    setLimitErrorInfo(null) // Clear any previous limit info
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/generate/complete-test/start', {
        method: 'POST',
        headers,
        body: JSON.stringify(testRequest)
      })
      
      if (response.ok) {
        const data = await response.json()
        setCurrentJobId(data.job_id)
        setIsPreparing(false) // Hide preparation state
        console.log('🚀 JOB CREATED:', data.job_id)
      } else {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.error || 'Failed to start test generation'
        setError(errorMessage)
        
        // Handle limit exceeded errors specially
        if (errorData.limit_exceeded && errorData.limits_info) {
          setLimitErrorInfo(errorData.limits_info)
        } else {
          setLimitErrorInfo(null)
        }
        
        setIsPreparing(false) // Hide preparation state on error
        console.error('Failed to start generation:', errorMessage)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Error starting generation'
      setError(errorMessage)
      setLimitErrorInfo(null)
      setIsPreparing(false) // Hide preparation state on error
      console.error('Error starting generation:', error)
    }
  }

  const handleGenerateAnother = () => {
    // Clear current job status
    setJobStatus(null)
    setCurrentJobId(null)
    
    // Show preparation state immediately
    setIsPreparing(true)
    
    // Create a new job with the same test request
    if (testRequest) {
      startGeneration(testRequest)
    }
  }

  const handleBackToForms = () => {
    setShowCompleteTest(false)
    setTestRequest(null)
    setJobStatus(null) // Clear jobStatus so new generation can start
    setCurrentJobId(null)
    setIsPreparing(false) // Clear preparation state
    setError(null) // Clear any errors
    setLimitErrorInfo(null) // Clear limit error info
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-12">
        {/* Page Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {t('Complete Practice Test')}
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            {t('Generate comprehensive SSAT practice tests with multiple sections')}
          </p>
        </div>

        <div className="max-w-6xl mx-auto space-y-8">
          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-800 mb-2">
                    {t('Daily limit exceeded')}
                  </h3>
                  <p className="text-red-700 mb-3">{error}</p>
                  
                  {limitErrorInfo && (
                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg max-w-lg">
                      <p className="text-blue-800 text-sm">
                        {t('Tip: Check your daily usage in your profile dropdown to see your current limits.')}
                      </p>
                      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg max-w-md">
                        <p className="text-gray-700 text-sm font-medium mb-2">{t('Current Usage:')}</p>
                        <div className="grid grid-cols-1 gap-1 text-xs text-gray-600">
                          <div className="flex justify-between">
                            <span>{t('Math')}:</span>
                            <span className="font-mono">{limitErrorInfo.usage.quantitative_generated}/{limitErrorInfo.limits.quantitative}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>{t('Analogy')}:</span>
                            <span className="font-mono">{limitErrorInfo.usage.analogy_generated}/{limitErrorInfo.limits.analogy}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>{t('Synonyms')}:</span>
                            <span className="font-mono">{limitErrorInfo.usage.synonyms_generated}/{limitErrorInfo.limits.synonyms}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>{t('Reading')}:</span>
                            <span className="font-mono">{limitErrorInfo.usage.reading_passages_generated}/{limitErrorInfo.limits.reading_passages}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>{t('Writing')}:</span>
                            <span className="font-mono">{limitErrorInfo.usage.writing_generated}/{limitErrorInfo.limits.writing}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="mt-4">
                    <button
                      onClick={handleBackToForms}
                      className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                      {t('Go Back to Configure')}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!showCompleteTest ? (
            /* Complete Test Configuration Form */
            <CompleteTestForm
              onSubmit={handleGenerateCompleteTest}
              loading={false} // Loading is handled by ProgressiveTestGenerator
              showChinese={showChinese}
            />
          ) : (
            /* Progressive Test Generator */
            <div className="space-y-6">
              {/* Progressive Test Generator */}
              {testRequest && (
                <ProgressiveTestGenerator
                  testRequest={testRequest}
                  showChinese={showChinese}
                  initialJobId={currentJobId || undefined}
                  onGenerateAnother={handleGenerateAnother}
                  onBack={handleBackToForms}
                  isPreparing={isPreparing}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
