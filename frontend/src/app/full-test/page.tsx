'use client'

import { ProgressiveTestGenerator } from '@/components/ProgressiveTestGenerator'
import { CompleteTestForm } from '@/components/forms/CompleteTestForm'
import { useFullTestState, useFullTestActions, usePreferences } from '@/contexts/AppStateContext'

export default function FullTestPage() {
  // Use global state for persistent data (testRequest, showCompleteTest, jobStatus)
  const { testRequest, showCompleteTest, jobStatus } = useFullTestState()
  const { setTestRequest, setShowCompleteTest, setJobStatus } = useFullTestActions()
  const { showChinese } = usePreferences()

  // UI translations (for future language support)  
  // const t = (key: string, showChinese: boolean = false) => key

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
      // Use official SSAT Elementary format - separate verbal into analogy and synonym
      newTestRequest = {
        difficulty: 'Medium',
        include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'],
        custom_counts: { 
          quantitative: 30, 
          analogy: 15, 
          synonym: 15, 
          reading: 28, 
          writing: 1 
        }
      }
    }
    
    setTestRequest(newTestRequest)
    
    // Show the progressive test generator
    setShowCompleteTest(true)
  }

  const handleBackToForms = () => {
    setShowCompleteTest(false)
    setTestRequest(null)
    setJobStatus(null) // Clear jobStatus so new generation can start
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-12">
        {/* Page Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Complete Practice Test
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Generate comprehensive SSAT practice tests with multiple sections
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
              {/* Back Button */}
              <div className="flex justify-start">
                <button
                  onClick={handleBackToForms}
                  className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-medium"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  <span>Back to Configuration</span>
                </button>
              </div>

              {/* Progressive Test Generator */}
              {testRequest && (
                <ProgressiveTestGenerator
                  testRequest={testRequest}
                  showChinese={showChinese}
                  autoStart={!jobStatus} // Only auto-start if no existing job
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}