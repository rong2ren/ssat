'use client'

import { useState, useEffect, useRef } from 'react'
import { TestSection } from '@/types/api'
import { TestDisplay } from './TestDisplay'
import { Button } from './ui/Button'
import { RefreshCw, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useFullTestState, useFullTestActions } from '@/contexts/AppStateContext'

interface ProgressiveTestGeneratorProps {
  showChinese: boolean
  onBack?: () => void
  autoStart?: boolean
  testRequest?: {
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[]
    is_official_format?: boolean
  }
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial' | 'cancelled'
  progress: {
    completed: number
    total: number
    percentage: number
  }
  sections: TestSection[]
  section_details: Record<string, {
    section_type: string
    status: string
    progress_percentage: number
    progress_message: string
    error?: string
  }>
  error?: string
  created_at: string
  updated_at: string
}

export function ProgressiveTestGenerator({ 
  showChinese, 
  onBack,
  autoStart = false,
  testRequest
}: ProgressiveTestGeneratorProps) {
  // Use context for persistent data (jobStatus, completedSections) and local state for active generation
  const { jobStatus: contextJobStatus } = useFullTestState()
  const { setJobStatus: contextSetJobStatus } = useFullTestActions()
  
  // Local state for active generation (prevents re-render loops)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(contextJobStatus)
  
  const [error, setError] = useState<string | null>(null)
  
  // Keep local state for current session-specific data
  const [jobId, setJobId] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [elapsedTime, setElapsedTime] = useState<string>('0s')
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const elapsedTimerRef = useRef<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // UI translations
  const translations = {
    'Generate Another Test': '生成另一个测试',
    'Back to Form': '返回表单',
    'Complete Test Generation': '完整测试生成',
    'Sections appear as they complete': '各部分完成后显示',
    'Generation Progress': '进度',
    'Elapsed': '已用时间',
    'Status': '状态',
    'Sections Complete': '完成部分',
    'Quantitative': '数学',
    'Verbal': '语言',
    'Reading': '阅读',
    'Writing': '写作',
    'Verbal - Analogies': '语言 - 类比',
    'Verbal - Synonyms': '语言 - 同义词',
    'Complete': '完成',
    'Generating...': '生成中',
    'Waiting': '等待',
    'Test Generation Complete!': '测试生成完成！',
    'Generated': '已生成',
    'sections in': '个部分，用时',
    'Your complete SSAT practice test is ready.': '您的完整SSAT练习测试已准备就绪。',
    'Generation Error': '生成错误',
    'pending': '等待中',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'questions': '题',
    'question': '题',
    'Complete SSAT Practice Test': '完整SSAT练习测试',
    'Test sections': '包含',
    'LIVE': '实时',
    'Generating Test': '正在生成测试',
    'Test Complete': '已完成',
        'Test Failed': '生成失败',
    'elapsed': '已用时',
    'sections complete': '部分已完成',
    'Job was deleted or no longer exists. The test generation may have failed or been cleaned up.': '任务已删除或不存在。测试生成可能失败或被清理。'
    }
  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  // Official SSAT Elementary format
  const defaultTestRequest = {
    difficulty: 'Medium',
    include_sections: ['quantitative', 'verbal', 'reading', 'writing'],
    custom_counts: { quantitative: 30, verbal: 30, reading: 28, writing: 1 },
    is_official_format: true
  }

  // Ensure finalTestRequest always has complete required fields
  const finalTestRequest = {
    difficulty: testRequest?.difficulty || defaultTestRequest.difficulty,
    include_sections: testRequest?.include_sections || defaultTestRequest.include_sections,
    custom_counts: testRequest?.custom_counts || defaultTestRequest.custom_counts,
    originalSelection: testRequest?.originalSelection,
    is_official_format: testRequest?.is_official_format ?? defaultTestRequest.is_official_format
  }

  // Cleanup function to stop all active operations
  const cleanup = () => {
    // Cancel any ongoing requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    // Stop polling
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }
    
    // Stop elapsed timer
    stopElapsedTimeCounter()
    
    // Reset polling state
    setIsPolling(false)
  }

  const startGeneration = async () => {
    // Prevent duplicate submissions
    if (isSubmitting) {
      return
    }
    
    // Prevent starting if there's already any job (running, pending, or completed)
    if (jobStatus) {
      return
    }

    // Validate required fields
    if (!finalTestRequest.include_sections || finalTestRequest.include_sections.length === 0) {
      setError('No sections selected for test generation')
      return
    }

    // Validate custom_counts
    if (!finalTestRequest.custom_counts || typeof finalTestRequest.custom_counts !== 'object') {
      setError('Invalid test configuration')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      
      // Cleanup any previous operations
      cleanup()
      
      const now = new Date()
      setStartTime(now)
      
      // Start elapsed time counter
      startElapsedTimeCounter(now)
      
      // Create initial job status with all sections in waiting state
      const initialJobStatus: JobStatus = {
        job_id: '',
        status: 'pending',
        progress: {
          completed: 0,
          total: finalTestRequest.include_sections.length,
          percentage: 0
        },
        sections: [],
        section_details: finalTestRequest.include_sections.reduce((acc, section) => {
          acc[section] = {
            section_type: section,
            status: 'waiting',
            progress_percentage: 0,
            progress_message: 'Waiting'
          }
          return acc
        }, {} as Record<string, {
          section_type: string
          status: string
          progress_percentage: number
          progress_message: string
          error?: string
        }>),
        error: undefined,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      // Set the initial status immediately
      console.log('🟢 SETTING INITIAL JOBSTATUS:', {
        sectionsCount: Object.keys(initialJobStatus.section_details).length,
        sections: Object.keys(initialJobStatus.section_details),
        progress: initialJobStatus.progress,
        fullSectionDetails: initialJobStatus.section_details
      })
      setJobStatus(initialJobStatus)
      
      // Create abort controller for this request
      abortControllerRef.current = new AbortController()
      
      // Add timeout to prevent hanging
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort()
        }
      }, 10000) // 10 second timeout for job creation
      
      // Send request to start test generation
      let requestBody: string
      try {
        requestBody = JSON.stringify(finalTestRequest)
        if (!requestBody || requestBody === '{}' || requestBody === 'null') {
          throw new Error('Invalid request data')
        }
        console.log('📤 DEBUG: Sending request to backend:', finalTestRequest)
        // Request body validated and ready
      } catch (jsonError) {
        console.error('Failed to serialize request:', jsonError, finalTestRequest)
        throw new Error('Failed to prepare request data')
      }
      
      const response = await fetch('/api/generate/complete-test/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: requestBody,
        signal: abortControllerRef.current.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setJobId(data.job_id)
      setIsPolling(true)
      
      // Update job status with real job ID and set all sections to generating
      setJobStatus((prev: JobStatus | null) => {
        console.log('🔵 UPDATING JOBSTATUS WITH JOB ID:', {
          hasJobStatus: !!prev,
          sectionsCount: prev?.section_details ? Object.keys(prev.section_details).length : 0,
          jobId: data.job_id,
          newStatus: 'running'
        })
        
        if (!prev) return null
        
        // Update all sections to generating status when job starts running
        const updatedSectionDetails = Object.keys(prev.section_details).reduce((acc, sectionKey) => {
          acc[sectionKey] = {
            ...prev.section_details[sectionKey],
            status: 'generating',
            progress_percentage: 25,
            progress_message: 'Preparing generation...'
          }
          return acc
        }, {} as Record<string, {
          section_type: string
          status: string
          progress_percentage: number
          progress_message: string
          error?: string
        }>)
        
        return {
          ...prev,
          job_id: data.job_id,
          status: 'running' as const,
          section_details: updatedSectionDetails
        }
      })
      
      // Start polling for updates
      startPolling(data.job_id)
      
    } catch (err) {
      // Handle abort differently from real errors
      if (err instanceof Error && err.name === 'AbortError') {
        return
      }
      
      setError(err instanceof Error ? err.message : 'Failed to start test generation')
      // Reset job status on error  
      console.log('🔴 CLEARING JOBSTATUS DUE TO ERROR:', err)
      setJobStatus(null)
      // Stop elapsed timer on error
      cleanup()
      // Only reset isSubmitting on error
      setIsSubmitting(false)
    }
    // Note: isSubmitting stays true until job completes/fails
  }

  const startElapsedTimeCounter = (startTime: Date) => {
    const updateElapsed = () => {
      const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000)
      let newElapsedTime: string
      if (elapsed < 60) {
        newElapsedTime = `${elapsed}s`
      } else {
        const minutes = Math.floor(elapsed / 60)
        const seconds = elapsed % 60
        newElapsedTime = `${minutes}m ${seconds}s`
      }
      
      setElapsedTime(newElapsedTime)
    }
    
    // Update immediately
    updateElapsed()
    
    // Then update every second
    elapsedTimerRef.current = window.setInterval(updateElapsed, 1000)
  }

  const stopElapsedTimeCounter = () => {
    if (elapsedTimerRef.current) {
      window.clearInterval(elapsedTimerRef.current)
      elapsedTimerRef.current = null
    }
  }

  const startPolling = (jobId: string) => {
    const poll = async () => {
      try {
        // Create abort controller for polling requests
        const pollAbortController = new AbortController()
        
        // Set timeout for individual polling requests (5 seconds)
        const timeoutId = setTimeout(() => {
          pollAbortController.abort()
        }, 5000)
        
        const response = await fetch(`/api/generate/complete-test/${jobId}/status`, {
          signal: pollAbortController.signal
        })
        
        clearTimeout(timeoutId)
        
        if (!response.ok) {
          // Handle "Not Found" specifically - job was deleted or doesn't exist
          if (response.status === 404) {
            console.log('🔴 Job not found (404), setting status to failed')
            const failedStatus: JobStatus = {
              job_id: jobId,
              status: 'failed',
              progress: {
                completed: 0,
                total: finalTestRequest.include_sections.length,
                percentage: 0
              },
              sections: [],
              section_details: {},
              error: t('Job was deleted or no longer exists. The test generation may have failed or been cleaned up.'),
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
            setJobStatus(failedStatus)
            setIsPolling(false)
            setIsSubmitting(false)
            stopElapsedTimeCounter()
            if (pollingRef.current) {
              clearTimeout(pollingRef.current)
              pollingRef.current = null
            }
            return
          }
          throw new Error(`Failed to get status: ${response.statusText}`)
        }

        const status: JobStatus = await response.json()
        
        // Debug: Log what we received from backend
        console.log('🟢 POLLING RESPONSE:', {
          jobStatus: status.status,
          progress: status.progress,
          sectionDetails: status.section_details ? Object.keys(status.section_details).map(key => ({
            section: key,
            status: status.section_details[key].status,
            progress: status.section_details[key].progress_percentage,
            message: status.section_details[key].progress_message
          })) : [],
          fullSectionDetails: status.section_details,
          sectionDetailsKeys: status.section_details ? Object.keys(status.section_details) : []
        })
        
        // Debug: Log what we're setting in state
        console.log('🔵 SETTING JOBSTATUS:', {
          hasSectionDetails: !!status.section_details,
          sectionDetailsCount: status.section_details ? Object.keys(status.section_details).length : 0,
          sectionDetailsKeys: status.section_details ? Object.keys(status.section_details) : []
        })
        
        // Simply use the backend response - it should contain all the data we need
        const completeStatus: JobStatus = {
          ...status,
          sections: status.sections || [],
          section_details: status.section_details || {},
          progress: status.progress || { completed: 0, total: 0, percentage: 0 }
        }
        
        setJobStatus(completeStatus)

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'partial' || status.status === 'cancelled') {
          setIsPolling(false)
          setIsSubmitting(false)  // Reset isSubmitting when job actually completes
          stopElapsedTimeCounter()
          if (pollingRef.current) {
            clearTimeout(pollingRef.current)
            pollingRef.current = null
          }
          return
        }

        // Continue polling every 1 second to catch more updates
        pollingRef.current = setTimeout(poll, 1000) as NodeJS.Timeout
        
      } catch (err) {
        // Handle timeout and abort errors gracefully
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Polling request timed out, retrying...')
          // Retry after 3 seconds on timeout
          pollingRef.current = setTimeout(poll, 3000) as NodeJS.Timeout
          return
        }
        
        // Polling error occurred - set job status to failed
        console.log('🔴 Polling error occurred, setting status to failed:', err)
        const errorMessage = err instanceof Error ? err.message : 'Failed to get status'
        
        const failedStatus: JobStatus = {
          job_id: jobId,
          status: 'failed',
          progress: {
            completed: 0,
            total: finalTestRequest.include_sections.length,
            percentage: 0
          },
          sections: [],
          section_details: {},
          error: errorMessage,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
        
        setJobStatus(failedStatus)
        setError(errorMessage)
        setIsPolling(false)
        setIsSubmitting(false)
        stopElapsedTimeCounter()
      }
    }

    poll()
  }

  const resetGenerator = () => {
    // Clear current state (both local and context)
    console.log('🔴 CLEARING JOBSTATUS DUE TO RESET GENERATOR')
    
    // Clear context state FIRST (so it doesn't get synced back)
    contextSetJobStatus(null)
    
    // Then clear local state
    setJobId(null)
    setJobStatus(null)
    setError(null)
    setStartTime(null)
    setElapsedTime('0s')
    
    // Use cleanup function
    cleanup()
    
    // Start new generation immediately (no timeout needed)
    startGeneration()
  }

    // Cleanup polling and timers on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [])

  // Auto-start generation when autoStart prop is true and no job exists
  // Remove jobStatus from deps to prevent dependency loop
  useEffect(() => {
    if (autoStart && testRequest && !jobStatus) {
      startGeneration()
    }
  }, [autoStart, testRequest])

  // Sync context to local state when context changes
  useEffect(() => {
    if (contextJobStatus && !jobStatus) {
      setJobStatus(contextJobStatus)
    }
  }, [contextJobStatus, jobStatus])



  // Update context when jobStatus changes (for persistence across tab switches)
  useEffect(() => {
    if (jobStatus !== contextJobStatus) {
      contextSetJobStatus(jobStatus)
    }
  }, [jobStatus, contextJobStatus])




  // Get display name for sections with descriptive labels
  const getSectionDisplayName = (sectionType: string) => {
    const nameMap: Record<string, string> = {
      'quantitative': t('Quantitative'),
      'reading': t('Reading'),
      'writing': t('Writing'),
      'analogy': t('Verbal - Analogies'),
      'synonym': t('Verbal - Synonyms'),
      'verbal': t('Verbal')
    }
    return nameMap[sectionType] || sectionType.charAt(0).toUpperCase() + sectionType.slice(1)
  }

  const getSectionStatusIcon = (sectionType: string) => {
    if (!jobStatus?.section_details[sectionType]) return <Clock className="h-4 w-4 text-gray-400" />
    
    const detail = jobStatus.section_details[sectionType]
    switch (detail.status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'generating':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getSectionStatusText = (sectionType: string) => {
    if (!jobStatus?.section_details[sectionType]) return t('Waiting')
    
    const detail = jobStatus.section_details[sectionType]
    switch (detail.status) {
      case 'completed':
        return t('Complete')
      case 'generating':
        return t('Generating...')
      case 'failed':
        return `Failed: ${detail.error || 'Unknown error'}`
      default:
        return t('Waiting')
    }
  }

  const getSectionCount = (section: string) => {
    return (finalTestRequest.custom_counts as Record<string, number>)[section] || 0
  }

  const getQuestionText = (count: number) => {
    return count === 1 ? t('question') : t('questions')
  }

  const getStatusText = () => {
    if (!jobStatus) return t('Generating Test')
    
    switch (jobStatus.status) {
      case 'pending':
        return t('Starting Generation...')
      case 'running':
        return t('Generating Test')
      case 'completed':
        return t('Test Complete')
      case 'failed':
        return t('Test Failed')
      case 'partial':
        return t('Test Partially Complete')
      case 'cancelled':
        return t('Test Cancelled')
      default:
        return t('Generating Test')
    }
  }




  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">{t('Complete SSAT Practice Test')}</h2>
        
        {/* Test Sections Info */}
        <div className="flex flex-wrap items-center gap-1 sm:gap-2 mb-4 sm:mb-6">
          <span className="text-xs sm:text-sm text-gray-600">{t('Test sections')}:</span>
          {finalTestRequest.include_sections.map((section) => {
            const count = getSectionCount(section)
            const sectionName = getSectionDisplayName(section)
            return (
              <div
                key={section}
                className="inline-flex items-center px-1.5 sm:px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700"
              >
                <span className="hidden sm:inline">{sectionName}: </span>
                <span className="sm:hidden">{sectionName.split(' ')[0]}: </span>
                {count} {getQuestionText(count)}
              </div>
            )
          })}
        </div>



        



        {/* Controls */}
        <div className="flex items-center space-x-4 mb-6">
          {/* Empty for now - post-completion buttons below */}
          
          {/* Post-completion buttons */}
          {(jobStatus?.status === 'completed' || jobStatus?.status === 'partial') && (
            <>
              <Button 
                variant="outline" 
                onClick={resetGenerator}
                disabled={isSubmitting}
                className="flex items-center space-x-2"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                <span>{isSubmitting ? 'Starting...' : t('Generate Another Test')}</span>
              </Button>
              
              {onBack && (
                <Button 
                  variant="outline" 
                  onClick={onBack}
                  disabled={isSubmitting}
                  className="flex items-center space-x-2"
                >
                  <span>← {t('Back to Form')}</span>
                </Button>
              )}
            </>
          )}


        </div>

        {/* Progress Tracking - show when generating or completed */}
        {jobStatus && (
          <>
            {/* Prominent Status Card */}
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg p-3 sm:p-4 mb-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
                <div className="flex items-center space-x-2 sm:space-x-3">
                  <div className="flex items-center space-x-1 sm:space-x-2">
                    <div className="w-2 h-2 sm:w-3 sm:h-3 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="font-medium text-xs sm:text-sm">{t('LIVE')}</span>
                  </div>
                  <span className="text-base sm:text-lg font-semibold">{getStatusText()}</span>
                  <span className="text-blue-100 text-xs sm:text-sm">• {showChinese ? `${t('elapsed')}：${elapsedTime}` : `${elapsedTime} ${t('elapsed')}`}</span>
                </div>
                <div className="text-left sm:text-right">
                  <div className="text-sm sm:text-lg font-bold">
                    <span className="sm:hidden">{jobStatus?.progress?.completed || 0}/{jobStatus?.progress?.total || 0}</span>
                    <span className="hidden sm:inline">{jobStatus?.progress?.completed || 0}/{jobStatus?.progress?.total || 0} {t('sections complete')}</span>
                    <span className="block sm:inline sm:ml-1">({jobStatus?.progress?.percentage || 0}%)</span>
                  </div>
                </div>
              </div>
              
              {/* Enhanced Progress Bar */}
              <div className="mt-3">
                <div className="w-full bg-blue-400 bg-opacity-30 rounded-full h-3">
                  <div 
                    className="bg-white h-3 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                    style={{ width: `${Math.max(jobStatus?.progress?.percentage || 0, 8)}%` }}
                  >
                    <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Section Status */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2 mb-4">
              {(() => {
                return Object.keys(jobStatus?.section_details || {}).map((sectionType) => (
                  <div key={sectionType} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg">
                    {getSectionStatusIcon(sectionType)}
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-gray-900 text-xs sm:text-sm truncate">{getSectionDisplayName(sectionType)}</div>
                      <div className="text-xs text-gray-600 truncate">{getSectionStatusText(sectionType)}</div>
                    </div>
                  </div>
                ))
              })()}
            </div>
            
            {/* Explanatory text at bottom */}
            <p className="text-gray-500 text-sm">{t('Sections appear as they complete')}</p>
          </>
        )}
      </div>


      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-500 mr-3" />
            <div>
              <h3 className="font-medium text-red-800">{t('Generation Error')}</h3>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Progressive Test Display */}
      {jobStatus && jobStatus.sections && jobStatus.sections.length > 0 && (
        <TestDisplay 
          sections={jobStatus.sections} 
          showChinese={showChinese}
        />
      )}

    </div>
  )
}