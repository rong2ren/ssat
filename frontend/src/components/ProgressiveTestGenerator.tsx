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
      'quantitative': 'Quantitative',
      'reading': 'Reading',
      'writing': 'Writing',
      'analogy': 'Verbal - Analogies',
      'synonym': 'Verbal - Synonyms',
      'verbal': 'Verbal (Mixed)'
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
        return 'Complete'
      case 'generating':
        return 'Generating...'
      case 'failed':
        return `Failed: ${detail.error || 'Unknown error'}`
      default:
        return 'Waiting'
    }
  }


  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-semibold text-gray-800">Complete Test Generation</h2>
            <p className="text-gray-600">
              Sections appear as they complete
            </p>
          </div>
          
          {onBack && (
            <Button variant="outline" onClick={onBack}>
              ← Back
            </Button>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-4">
          {isPolling && (
            <Button 
              variant="outline" 
              onClick={cancelGeneration}
              className="flex items-center space-x-2"
            >
              <Square className="h-4 w-4" />
              <span>Cancel</span>
            </Button>
          )}
          
          {jobStatus && !isPolling && (
            <Button 
              variant="outline" 
              onClick={resetGenerator}
              className="flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Generate New Test</span>
            </Button>
          )}
        </div>
      </div>

      {/* Progress Tracking */}
      {jobStatus && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Generation Progress</h3>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>Elapsed: {elapsedTime}</span>
              <span>Status: {jobStatus.status}</span>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Sections Complete: {jobStatus.progress.completed}/{jobStatus.progress.total}</span>
              <span>{jobStatus.progress.percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${jobStatus.progress.percentage}%` }}
              />
            </div>
          </div>
          
          {/* Section Status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.keys(jobStatus.section_details).map((sectionType) => (
              <div key={sectionType} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                {getSectionStatusIcon(sectionType)}
                <div>
                  <div className="font-medium text-gray-900">{getSectionDisplayName(sectionType)}</div>
                  <div className="text-sm text-gray-600">{getSectionStatusText(sectionType)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-red-500 mr-3" />
            <div>
              <h3 className="font-medium text-red-800">Generation Error</h3>
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

      {/* Completion Message */}
      {jobStatus?.status === 'completed' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center">
            <CheckCircle className="h-6 w-6 text-green-500 mr-3" />
            <div>
              <h3 className="font-medium text-green-800">Test Generation Complete!</h3>
              <p className="text-sm text-green-700">
                Generated {jobStatus.progress.total} sections in {elapsedTime}. 
                Your complete SSAT practice test is ready.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}