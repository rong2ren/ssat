'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getAuthHeaders } from '@/utils/auth'
import { Progress } from './ui/Progress'

// Global cache to prevent multiple API calls
const limitsCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_DURATION = 15 * 60 * 1000 // 15 minutes (increased from 5 minutes)

// Cache key for localStorage
const CACHE_STORAGE_KEY = 'daily_limits_cache'

// Load cache from localStorage on module load (only in browser)
const loadCacheFromStorage = () => {
  if (typeof window === 'undefined') return // Skip during SSR
  
  try {
    const stored = localStorage.getItem(CACHE_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      Object.entries(parsed).forEach(([key, value]: [string, any]) => {
        limitsCache.set(key, value)
      })
      console.log('🔍 DailyLimitsDisplay: Loaded cache from localStorage:', Object.keys(parsed))
    }
  } catch (error) {
    console.warn('Failed to load limits cache from localStorage:', error)
  }
}

// Initialize cache when component mounts (browser only)
if (typeof window !== 'undefined') {
  loadCacheFromStorage()
}

// Save cache to localStorage
const saveCacheToStorage = () => {
  try {
    const cacheObj = Object.fromEntries(limitsCache.entries())
    localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(cacheObj))
  } catch (error) {
    console.warn('Failed to save limits cache to localStorage:', error)
  }
}

// Function to invalidate cache for a user
export const invalidateLimitsCache = (userId?: string) => {
  if (userId) {
    limitsCache.delete(userId)
    saveCacheToStorage()
    console.log('🔍 DailyLimitsDisplay: Invalidated cache for user:', userId)
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
    synonyms_generated: number
    reading_passages_generated: number
    writing_generated: number
  }
  limits: {
    quantitative: number
    analogy: number
    synonyms: number
    reading_passages: number
    writing: number
  }
  remaining: {
    quantitative: number
    analogy: number
    synonyms: number
    reading_passages: number
    writing: number
  }
}

function DailyLimitsDisplayComponent({ showChinese = false, className = '' }: DailyLimitsDisplayProps) {
  const { user } = useAuth()
  const [limits, setLimits] = useState<LimitsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
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
    'Today': '今日'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  // Fetch limits once when component mounts
  useEffect(() => {
    const fetchLimits = async () => {
      if (!user) {
        setLoading(false)
        return
      }

      // Check cache first
      const cached = limitsCache.get(user.id)
      const now = Date.now()
      if (cached && (now - cached.timestamp) < CACHE_DURATION) {
        console.log('🔍 DailyLimitsDisplay: Using cached limits for user:', user.id)
        setLimits(cached.data)
        setLoading(false)
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

      try {
        const headers = await getAuthHeaders()
        const response = await fetch('/api/user/limits', {
          headers,
          // Add cache control to prevent unnecessary refetches
          cache: 'default'
        })

        if (!response.ok) {
          throw new Error('Failed to fetch limits')
        }

        const data = await response.json()
        if (data.success && data.data) {
          setLimits(data.data)
          // Cache the result
          limitsCache.set(user.id, { data: data.data, timestamp: now })
          saveCacheToStorage() // Save to localStorage
          console.log('🔍 DailyLimitsDisplay: Successfully fetched and cached limits')
        } else {
          throw new Error('Invalid response format')
        }
      } catch (err) {
        console.error('Error fetching daily limits:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
        hasFetchedRef.current = false // Reset on error so we can retry
      } finally {
        setLoading(false)
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
    { key: 'synonyms', label: 'Synonyms', used: usage.synonyms_generated, limit: limitsData.synonyms, remaining: remaining.synonyms },
    { key: 'reading_passages', label: 'Reading Passages', used: usage.reading_passages_generated, limit: limitsData.reading_passages, remaining: remaining.reading_passages },
    { key: 'writing', label: 'Writing', used: usage.writing_generated, limit: limitsData.writing, remaining: remaining.writing }
  ]

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-gray-900">
          {t('Daily Limits')}
        </h3>
        <div className="text-xs text-gray-500">
          {loading ? t('Loading...') : t('Today')}
        </div>
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
                <div className="relative">
                  <Progress 
                    value={percentage}
                    className="h-1.5 bg-gray-200"
                    indicatorClassName={`${color} rounded-full`}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export const DailyLimitsDisplay = React.memo(DailyLimitsDisplayComponent)