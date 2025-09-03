'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getAuthHeaders } from '@/utils/auth'
import { Progress } from './ui/Progress'

const CACHE_DURATION = 15 * 60 * 1000 // 15 minutes

// Helper functions for localStorage cache
const getCacheKey = (userId: string) => `daily-limits-cache-${userId}`

const getCachedLimits = (userId: string) => {
  try {
    // SSR safety check
    if (typeof window === 'undefined') return null
    
    const stored = localStorage.getItem(getCacheKey(userId))
    if (stored) {
      const parsed = JSON.parse(stored)
      const now = Date.now()
      if (parsed.timestamp && (now - parsed.timestamp) < CACHE_DURATION) {
        console.log('🔍 DailyLimitsDisplay: Using cached limits for user:', userId)
        return parsed.data
      } else {
        // Clean up ALL expired cache entries, not just this user's
        console.log('🔍 DailyLimitsDisplay: Removing expired cache for user:', userId)
        cleanupExpiredCache()
      }
    }
  } catch (error) {
    console.warn('Failed to load limits cache from localStorage:', error)
  }
  return null
}

const setCachedLimits = (userId: string, data: any) => {
  try {
    // SSR safety check
    if (typeof window === 'undefined') return
    
    const cacheData = { data, timestamp: Date.now() }
    localStorage.setItem(getCacheKey(userId), JSON.stringify(cacheData))
    console.log('🔍 DailyLimitsDisplay: Cached limits for user:', userId)
  } catch (error) {
    console.warn('Failed to save limits cache to localStorage:', error)
  }
}

const clearUserCache = (userId: string) => {
  try {
    // SSR safety check
    if (typeof window === 'undefined') return
    
    localStorage.removeItem(getCacheKey(userId))
    console.log('🔍 DailyLimitsDisplay: Cleared cache for user:', userId)
  } catch (error) {
    console.warn('Failed to clear user cache:', error)
  }
}

// Track ongoing requests to prevent cache stampede
const ongoingRequests = new Map<string, Promise<any>>()

// Function to invalidate cache for a user
export const invalidateLimitsCache = (userId?: string) => {
  if (userId) {
    // Immediate cache invalidation to prevent stale data
    clearUserCache(userId)
    // Clear any ongoing request for this user
    ongoingRequests.delete(userId)
  }
}

// Function to reset fetch flag so component can re-fetch
export const resetDailyLimitsFetch = () => {
  // Dispatch custom event to trigger re-fetch
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('dailyLimitsRefresh'))
  }
}

// Function to clear all cache (for logout)
export const clearAllLimitsCache = () => {
  try {
    // SSR safety check
    if (typeof window === 'undefined') return
    
    // More efficient: only iterate through keys that match our pattern
    let cleanedCount = 0
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('daily-limits-cache-')) {
        localStorage.removeItem(key)
        cleanedCount++
      }
    }
    
    if (cleanedCount > 0) {
      console.log(`🔍 DailyLimitsDisplay: Cleared ${cleanedCount} cache entries`)
    }
  } catch (error) {
    console.warn('Failed to clear localStorage cache:', error)
  }
}

// Function to clean up expired cache entries
const cleanupExpiredCache = () => {
  try {
    // SSR safety check
    if (typeof window === 'undefined') return
    
    let cleanedCount = 0
    
    // Remove all daily-limits-cache-* entries
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('daily-limits-cache-')) {
        localStorage.removeItem(key)
        cleanedCount++
      }
    }
    
    if (cleanedCount > 0) {
      console.log(`🔍 DailyLimitsDisplay: Cleaned up ${cleanedCount} cache entries`)
    }
  } catch (error) {
    console.warn('Failed to cleanup expired cache:', error)
  }
}

interface DailyLimitsDisplayProps {
  showChinese?: boolean
  className?: string
}

interface LimitsData {
  usage: {
    quantitative_generated: number
    analogy_generated: number
    synonym_generated: number
    reading_passages_generated: number
    writing_generated: number
  }
  limits: {
    quantitative: number
    analogy: number
    synonym: number
    reading_passages: number
    writing: number
  }
  remaining: {
    quantitative: number
    analogy: number
    synonym: number
    reading_passages: number
    writing: number
  }
}

function DailyLimitsDisplayComponent({ showChinese = false, className = '' }: DailyLimitsDisplayProps) {
  const { user } = useAuth()
  const [limits, setLimits] = useState<LimitsData | null>(null)
  const [loading, setLoading] = useState(true) // Start with loading to prevent hydration mismatch
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const hasFetchedRef = useRef(false) // Track if we've already fetched data

  // UI translations
  const translations = {
    'Daily Limits': '每日限制',
    'Quantitative': '数学',
    'Analogy': '类比',
    'Synonyms': '同义词',
    'Reading Passages': '阅读段落',
    'Writing': '写作',
    'remaining': '剩余',
    'of': '共',
    'left': '剩余',
    'Loading daily limits...': '正在加载每日使用限制...',
    'Failed to load limits': '每日使用限制加载失败',
    'Loading...': '正在加载...',
    'Refresh': '刷新'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  // Force refresh function
  const forceRefresh = async () => {
    if (!user) return
    
    setRefreshing(true)
    setError(null)
    
    try {
      // Clear cache for this user
      clearUserCache(user.id)
      
      // Reset fetch flag to allow new fetch
      hasFetchedRef.current = false
      
      const headers = await getAuthHeaders()
      const response = await fetch('/api/user/limits', {
        headers,
        cache: 'no-cache' // Force fresh data
      })

      if (!response.ok) {
        throw new Error('Failed to fetch limits')
      }

      const data = await response.json()
      if (data.success && data.data) {
        setLimits(data.data)
        // Cache the fresh result
        setCachedLimits(user.id, data.data)
        console.log('🔍 DailyLimitsDisplay: Force refreshed limits from backend')
      } else {
        throw new Error('Invalid response format')
      }
    } catch (err) {
      console.error('Error force refreshing daily limits:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setRefreshing(false)
    }
  }

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = () => {
      console.log('🔍 DailyLimitsDisplay: Refresh event received, resetting fetch state')
      hasFetchedRef.current = false
      // Force a re-render to trigger the fetch
      setLoading(true)
    }

    window.addEventListener('dailyLimitsRefresh', handleRefresh)
    return () => window.removeEventListener('dailyLimitsRefresh', handleRefresh)
  }, [])

  // Fetch limits once when component mounts
  useEffect(() => {
    const fetchLimits = async () => {
      if (!user) {
        setLoading(false)
        return
      }

      // Check cache first
      const cached = getCachedLimits(user.id)
      if (cached) {
        setLimits(cached)
        setLoading(false)
        return
      }

      // Check if there's an ongoing request for this user
      const ongoingRequest = ongoingRequests.get(user.id)
      if (ongoingRequest) {
        console.log('🔍 DailyLimitsDisplay: Reusing ongoing request for user:', user.id)
        try {
          const data = await ongoingRequest
          setLimits(data)
          setLoading(false)
        } catch (error) {
          console.error('Error from ongoing request:', error)
          setError(error instanceof Error ? error.message : 'Unknown error')
          setLoading(false)
        }
        return
      }

      // Don't fetch if we've already fetched for this user in this session
      if (hasFetchedRef.current) {
        console.log('🔍 DailyLimitsDisplay: Already fetched limits in this session, skipping API call')
        return
      }

      console.log('🔍 DailyLimitsDisplay: Fetching limits for user:', user.id)
      hasFetchedRef.current = true

      setLoading(true)
      setError(null)

      // Create the request promise and store it
      const requestPromise = (async () => {
        try {
          const headers = await getAuthHeaders()
          const response = await fetch('/api/user/limits', {
            headers,
            cache: 'default'
          })

          if (!response.ok) {
            throw new Error('Failed to fetch limits')
          }

          const data = await response.json()
          if (data.success && data.data) {
            // Cache the result
            setCachedLimits(user.id, data.data)
            console.log('🔍 DailyLimitsDisplay: Successfully fetched and cached limits')
            return data.data
          } else {
            throw new Error('Invalid response format')
          }
        } catch (error) {
          console.error('Error fetching daily limits:', error)
          throw error
        }
      })()

      // Store the request promise
      ongoingRequests.set(user.id, requestPromise)

      try {
        const data = await requestPromise
        setLimits(data)
        console.log('🔍 DailyLimitsDisplay: Successfully fetched limits')
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Unknown error')
        hasFetchedRef.current = false // Reset on error so we can retry
      } finally {
        setLoading(false)
        // Clean up the request promise
        ongoingRequests.delete(user.id)
      }
    }

    fetchLimits()
  }, [user?.id]) // Use user.id instead of user object to prevent unnecessary re-renders

  if (!user) {
    return null
  }

  if (loading) {
    return (
      <div className={`text-sm text-gray-600 ${className}`}>
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600"></div>
          <span>{t('Loading daily limits...')}</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`text-sm text-red-600 ${className}`}>
        {t('Failed to load limits')}
      </div>
    )
  }

  if (!limits) {
    return (
      <div className={`space-y-3 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-3 bg-gray-200 rounded w-20 animate-pulse"></div>
          <div className="h-3 bg-gray-200 rounded w-12 animate-pulse"></div>
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-2">
              <div className="flex items-center justify-between mb-1">
                <div className="h-3 bg-gray-200 rounded w-16 animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-12 animate-pulse"></div>
              </div>
              <div className="h-1.5 bg-gray-200 rounded animate-pulse"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const { usage, limits: limitsData, remaining } = limits

  const getProgressPercentage = (used: number, total: number) => {
    if (total === -1) return 0 // Unlimited
    return Math.min((used / total) * 100, 100)
  }

  const getProgressColor = (percentage: number, limit: number) => {
    if (limit === -1) return 'bg-green-500' // Unlimited
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 75) return 'bg-yellow-500'
    return 'bg-blue-500'
  }

  const sections = [
    { key: 'quantitative', label: 'Quantitative', used: usage.quantitative_generated, limit: limitsData.quantitative, remaining: remaining.quantitative },
    { key: 'analogy', label: 'Analogy', used: usage.analogy_generated, limit: limitsData.analogy, remaining: remaining.analogy },
    { key: 'synonym', label: 'Synonyms', used: usage.synonym_generated, limit: limitsData.synonym, remaining: remaining.synonym },
    { key: 'reading_passages', label: 'Reading Passages', used: usage.reading_passages_generated, limit: limitsData.reading_passages, remaining: remaining.reading_passages },
    { key: 'writing', label: 'Writing', used: usage.writing_generated, limit: limitsData.writing, remaining: remaining.writing }
  ]

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-gray-900">
          {t('Daily Limits')}
        </h3>
        <button
          onClick={forceRefresh}
          disabled={refreshing || loading}
          className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title={t('Refresh limits from backend')}
        >
          <svg 
            className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{refreshing ? t('Loading...') : t('Refresh')}</span>
        </button>
      </div>
      
      <div className="space-y-2">
        {sections.map((section) => {
          const percentage = getProgressPercentage(section.used, section.limit)
          const color = getProgressColor(percentage, section.limit)
          const isUnlimited = section.limit === -1
          
          return (
            <div key={section.key} className="bg-gray-50 rounded-lg p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700 truncate">
                  {t(section.label)}
                </span>
                <div className="flex items-center space-x-1">
                  {isUnlimited ? (
                    <span className="text-xs text-green-600 font-medium">∞</span>
                  ) : (
                    <>
                      <span className="text-xs text-gray-500">
                        {section.used}/{section.limit}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">
                        {section.remaining} {t('left')}
                      </span>
                    </>
                  )}
                </div>
              </div>
              {!isUnlimited && (
                <Progress 
                  value={percentage} 
                  className="h-1.5" 
                  indicatorClassName={color}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export const DailyLimitsDisplay = React.memo(DailyLimitsDisplayComponent)