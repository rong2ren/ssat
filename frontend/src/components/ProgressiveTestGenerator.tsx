'use client'

import { useState, useEffect, useRef } from 'react'
import { TestSection } from '@/types/api'
import { TestDisplay } from './TestDisplay'
import { Button } from './ui/Button'
import { Square, RefreshCw, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

interface ProgressiveTestGeneratorProps {
  showChinese: boolean
  onBack?: () => void
  testRequest?: {
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[]
  }
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
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
  testRequest
}: ProgressiveTestGeneratorProps) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [elapsedTime, setElapsedTime] = useState<string>('0s')
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const elapsedTimerRef = useRef<number | null>(null)

  // UI translations
  const translations = {
    'Generate Another Test': '生成另一个测试',
    'Back to Form': '返回表单',
    'Complete Test Generation': '完整测试生成',
    'Test sections appear as they complete': '各测试部分将在完成后依次显示',
    'Cancel': '取消',
    'Generation Progress': '进度',
    'Elapsed': '已用时间',
    'Status': '状态',
    'Sections Complete': '完成部分',
    'Quantitative': '数学',
    'Reading': '阅读',
    'Writing': '写作',
    'Verbal - Analogies': '语言 - 类比',
    'Verbal - Synonyms': '语言 - 同义词',
    'Verbal (Mixed)': '语言（混合）',
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
    'cancelled': '已取消',
    'questions': '题',
    'question': '题',
    'Sections appear as they complete': '各部分完成后显示',
    'Complete SSAT Practice Test': '完整SSAT练习测试',
    'Test sections': '包含',
    'LIVE': '实时',
    'Generating Test': '正在生成测试',
    'Test Complete': '已完成',
    'Test Failed': '生成失败',
    'Test Cancelled': '已取消',
    'elapsed': '已用时',
    'sections complete': '部分已完成'
  }
  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  // Default test configuration - Official SSAT Elementary sections with proper verbal distribution
  const defaultTestRequest = {
    difficulty: 'Medium',
    include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'],
    custom_counts: { quantitative: 10, analogy: 4, synonym: 6, reading: 7, writing: 1 }
  }

  const finalTestRequest = testRequest || defaultTestRequest

  const startGeneration = async () => {
    try {
      setError(null)
      const now = new Date()
      setStartTime(now)
      
      // Start elapsed time counter
      startElapsedTimeCounter(now)
      
      // Create initial job status to show progress section immediately
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
      
      // Show progress section immediately
      setJobStatus(initialJobStatus)
      
      const response = await fetch('/api/generate/complete-test/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(finalTestRequest),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setJobId(data.job_id)
      setIsPolling(true)
      
      // Update the initial status with the real job ID
      setJobStatus(prev => prev ? { ...prev, job_id: data.job_id, status: 'running' } : null)
      
      startPolling(data.job_id)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start test generation')
      // Reset job status on error
      setJobStatus(null)
      // Stop elapsed timer on error
      stopElapsedTimeCounter()
    }
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
        const response = await fetch(`/api/generate/complete-test/${jobId}/status`)
        
        if (!response.ok) {
          throw new Error(`Failed to get status: ${response.statusText}`)
        }

        const status: JobStatus = await response.json()
        setJobStatus(status)

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          setIsPolling(false)
          stopElapsedTimeCounter()
          if (pollingRef.current) {
            clearTimeout(pollingRef.current)
          }
          return
        }

        // Continue polling every 2 seconds
        pollingRef.current = setTimeout(poll, 2000) as NodeJS.Timeout
        
      } catch (err) {
        console.error('Polling error:', err)
        setError(err instanceof Error ? err.message : 'Failed to get status')
        setIsPolling(false)
        stopElapsedTimeCounter()
      }
    }

    poll()
  }

  const cancelGeneration = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`/api/generate/complete-test/${jobId}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        setIsPolling(false)
        stopElapsedTimeCounter()
        if (pollingRef.current) {
          clearTimeout(pollingRef.current)
        }
      }
    } catch (err) {
      console.error('Failed to cancel:', err)
    }
  }

  const resetGenerator = () => {
    // Clear current state
    setJobId(null)
    setJobStatus(null)
    setIsPolling(false)
    setError(null)
    setStartTime(null)
    setElapsedTime('0s')
    stopElapsedTimeCounter()
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
    }
    
    // Immediately start new generation with same settings
    setTimeout(() => {
      startGeneration()
    }, 100) // Small delay to ensure state is cleared
  }

  // Cleanup polling and timers on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current)
      }
      stopElapsedTimeCounter()
    }
  }, [])

  // Auto-start generation when component mounts
  useEffect(() => {
    startGeneration()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Get display name for sections with descriptive labels
  const getSectionDisplayName = (sectionType: string) => {
    const nameMap: Record<string, string> = {
      'quantitative': t('Quantitative'),
      'reading': t('Reading'),
      'writing': t('Writing'),
      'analogy': t('Verbal - Analogies'),
      'synonym': t('Verbal - Synonyms'),
      'verbal': t('Verbal (Mixed)')
    }
    return nameMap[sectionType] || sectionType.charAt(0).toUpperCase() + sectionType.slice(1)
  }

  const getSectionStatusIcon = (sectionType: string) => {
    if (!jobStatus?.section_details[sectionType]) return <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
    
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
    if (!jobStatus?.section_details[sectionType]) return 'Waiting'
    
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
      case 'completed':
        return t('Test Complete')
      case 'failed':
        return t('Test Failed')
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
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <span className="text-sm text-gray-600">{t('Test sections')}:</span>
          {finalTestRequest.include_sections.map((section) => {
            const count = getSectionCount(section)
            const sectionName = getSectionDisplayName(section)
            return (
              <div
                key={section}
                className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700"
              >
                {sectionName}: {count} {getQuestionText(count)}
              </div>
            )
          })}
        </div>

        {/* Controls - moved right below header */}
        <div className="flex items-center space-x-4 mb-6">
          {/* Cancel button - only during generation */}
          {isPolling && (
            <Button 
              variant="outline" 
              onClick={cancelGeneration}
              className="flex items-center space-x-2"
            >
              <Square className="h-4 w-4" />
              <span>{t('Cancel')}</span>
            </Button>
          )}
          
          {/* Post-completion buttons */}
          {jobStatus?.status === 'completed' && (
            <>
              <Button 
                variant="outline" 
                onClick={resetGenerator}
                className="flex items-center space-x-2"
              >
                <RefreshCw className="h-4 w-4" />
                <span>{t('Generate Another Test')}</span>
              </Button>
              
              {onBack && (
                <Button 
                  variant="outline" 
                  onClick={onBack}
                  className="flex items-center space-x-2"
                >
                  <span>← {t('Back to Form')}</span>
                </Button>
              )}
            </>
          )}
        </div>

        {/* Progress Tracking - integrated into header container */}
        {jobStatus && (
          <>
            {/* Prominent Status Card */}
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="font-medium text-sm">{t('LIVE')}</span>
                  </div>
                  <span className="text-lg font-semibold">{getStatusText()}</span>
                  <span className="text-blue-100">• {showChinese ? `${t('elapsed')}：${elapsedTime}` : `${elapsedTime} ${t('elapsed')}`}</span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold">
                    {jobStatus.progress.completed}/{jobStatus.progress.total} {t('sections complete')} ({jobStatus.progress.percentage}%)
                  </div>
                </div>
              </div>
              
              {/* Enhanced Progress Bar */}
              <div className="mt-3">
                <div className="w-full bg-blue-400 bg-opacity-30 rounded-full h-3">
                  <div 
                    className="bg-white h-3 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                    style={{ width: `${Math.max(jobStatus.progress.percentage, 8)}%` }}
                  >
                    <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Section Status */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
              {Object.keys(jobStatus.section_details).map((sectionType) => (
                <div key={sectionType} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg">
                  {getSectionStatusIcon(sectionType)}
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-gray-900 text-sm truncate">{getSectionDisplayName(sectionType)}</div>
                    <div className="text-xs text-gray-600 truncate">{getSectionStatusText(sectionType)}</div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Explanatory text at bottom */}
            <p className="text-gray-500 text-sm">{t('Test sections appear as they complete')}</p>
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
      {jobStatus && jobStatus.sections.length > 0 && (
        <TestDisplay 
          sections={jobStatus.sections} 
          showChinese={showChinese}
        />
      )}

    </div>
  )
}