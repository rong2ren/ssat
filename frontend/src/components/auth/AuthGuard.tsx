'use client'

import React, { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface AuthGuardProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

export default function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const authResultRef = useRef({ user, loading })
  
  // Log when useAuth() is actually called (this is the real authentication check)
  // Only log in development to avoid console spam
  if (process.env.NODE_ENV === 'development') {
    console.log('🔍 AuthGuard: useAuth() called - this is the actual auth check', { user: !!user, loading })
  }
  
  // Only log when auth result actually changes
  if (authResultRef.current.user !== user || authResultRef.current.loading !== loading) {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔍 AuthGuard: Auth state changed', { 
        user: !!user, 
        loading,
        previousUser: !!authResultRef.current.user,
        previousLoading: authResultRef.current.loading
      })
    }
    authResultRef.current = { user, loading }
  }

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth')
    }
  }, [user, loading, router])

  // Show loading while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Show fallback or redirect if not authenticated
  if (!user) {
    if (fallback) {
      return <>{fallback}</>
    }
    // Return loading state while redirecting
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  // User is authenticated, show children
  return <>{children}</>
} 