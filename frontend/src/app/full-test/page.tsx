'use client'

import { useState } from 'react'
import { ProgressiveTestGenerator } from '@/components/ProgressiveTestGenerator'
import { CompleteTestForm } from '@/components/forms/CompleteTestForm'
import { useFullTestState, useFullTestActions, usePreferences } from '@/contexts/AppStateContext'
import { getAuthHeaders } from '@/utils/auth'
import { useAuth } from '@/contexts/AuthContext'
import { invalidateLimitsCache } from '@/components/DailyLimitsDisplay'
import AuthGuard from '@/components/auth/AuthGuard'

export default function FullTestPage() {
  const { user } = useAuth()
  // Use global state instead of local state
  const { testRequest, showCompleteTest, jobStatus } = useFullTestState()
  const { setTestRequest, setShowCompleteTest, setJobStatus } = useFullTestActions()
  const { showChinese } = usePreferences()
  
  // Local state to store the job ID and preparation status
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [isPreparing, setIsPreparing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [limitErrorInfo, setLimitErrorInfo] = useState<any>(null)
  const [showUsageDetails, setShowUsageDetails] = useState(false)

  // UI translations
  const translations = {
    'Complete Practice Test': '完整模拟测试',
    'Generate comprehensive SSAT practice tests with multiple sections': '生成完整SSAT模拟测试题',
    'Daily limit exceeded': '已达到每日限制',
    'Go Back': '返回',
    'Current Usage:': '今日题型使用情况：',
    'Math': '数学',
    'Analogy': '类比',
    'Synonyms': '同义词',
    'Reading': '阅读',
    'Writing': '写作',
    'Tip: Check your daily usage in your profile dropdown to see your current limits.': '💡 提示：在您的个人资料下拉菜单中可以查看您的当前使用情况。',
    'Show usage details': '显示使用详情',
    'Hide usage details': '隐藏使用详情'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleGenerateCompleteTest = (customConfig?: {
    sections: string[]
    counts: Record<string, number>
    difficulty: string
  }) => {
    let newTestRequest
    if (customConfig) {
      // Use custom configuration - gets questions from existing pool
      newTestRequest = {
        difficulty: customConfig.difficulty,
        include_sections: customConfig.sections, // Send original sections directly
        custom_counts: customConfig.counts,
        originalSelection: customConfig.sections,
        is_official_format: false // Custom format from pool
      }
      console.log('🔧 DEBUG: Using CUSTOM format from pool:', newTestRequest)
    } else {
      // Use official SSAT Elementary format - separate verbal into analogy and synonyms
      newTestRequest = {
        difficulty: 'Medium',
        include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'],
        custom_counts: {
          quantitative: 30,  // 30 math questions
          analogy: 12,       // 40% of 30 = 12 questions
          synonym: 18,  // 60% of 30 = 18 questions
          reading: 7,        // 7 passages
          writing: 1         // 1 writing prompt
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
        console.log('🔍 FULL TEST: ✅ Test generation started successfully')
        
        // Invalidate limits cache to refresh the display
        if (user?.id) {
          invalidateLimitsCache(user.id)
          console.log('🔍 FULL TEST: Invalidated cache after test generation')
        }
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
    <AuthGuard>
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
              <div className="bg-gradient-to-br from-red-50 to-orange-50 border border-red-200 rounded-2xl p-8 shadow-lg">
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                      <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-red-800 mb-3">
                      {limitErrorInfo ? t('Daily limit exceeded') : t('Error')}
                    </h3>
                    <p className="text-red-700 mb-4 text-base leading-relaxed">{error}</p>
                    
                    {limitErrorInfo && (
                      <div className="mt-4">
                        <div className="flex items-start space-x-2">
                          <svg className="h-5 w-5 text-gray-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <p className="text-gray-700 text-sm font-medium leading-relaxed">
                            {t('Tip: Check your daily usage in your profile dropdown to see your current limits.')}
                          </p>
                        </div>
                        
                        <div className="mt-3">
                          <button
                            onClick={() => setShowUsageDetails(!showUsageDetails)}
                            className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 text-sm font-medium transition-colors"
                          >
                            <svg 
                              className={`h-4 w-4 transition-transform ${showUsageDetails ? 'rotate-180' : ''}`} 
                              fill="none" 
                              viewBox="0 0 24 24" 
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                            <span>{showUsageDetails ? t('Hide usage details') : t('Show usage details')}</span>
                          </button>
                          
                          {showUsageDetails && (
                            <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded-lg max-w-xs">
                              <p className="text-gray-800 text-xs font-semibold mb-1 flex items-center">
                                <svg className="h-3 w-3 mr-1 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                {t('Current Usage:')}
                              </p>
                              <div className="space-y-0.5 text-xs">
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-700 font-medium">{t('Math')}:</span>
                                  <span className="font-mono text-gray-900 font-semibold">{limitErrorInfo.usage.quantitative_generated}/{limitErrorInfo.limits.quantitative}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-700 font-medium">{t('Analogy')}:</span>
                                  <span className="font-mono text-gray-900 font-semibold">{limitErrorInfo.usage.analogy_generated}/{limitErrorInfo.limits.analogy}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-700 font-medium">{t('Synonyms')}:</span>
                                  <span className="font-mono text-gray-900 font-semibold">{limitErrorInfo.usage.synonym_generated}/{limitErrorInfo.limits.synonym}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-700 font-medium">{t('Reading')}:</span>
                                  <span className="font-mono text-gray-900 font-semibold">{limitErrorInfo.usage.reading_passages_generated}/{limitErrorInfo.limits.reading_passages}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-700 font-medium">{t('Writing')}:</span>
                                  <span className="font-mono text-gray-900 font-semibold">{limitErrorInfo.usage.writing_generated}/{limitErrorInfo.limits.writing}</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <div className="mt-6">
                      <button
                        onClick={handleBackToForms}
                        className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                      >
                        {t('Go Back')}
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
    </AuthGuard>
  )
}
