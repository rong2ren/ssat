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

  // UI translations
  const translations = {
    'Complete Practice Test': '完整模拟测试',
    'Generate comprehensive SSAT practice tests with multiple sections': '生成完整SSAT模拟测试题'
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
        console.error('Failed to start generation')
        setIsPreparing(false) // Hide preparation state on error
      }
    } catch (error) {
      console.error('Error starting generation:', error)
      setIsPreparing(false) // Hide preparation state on error
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
