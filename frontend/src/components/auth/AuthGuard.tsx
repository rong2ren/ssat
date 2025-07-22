'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface AuthGuardProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

export default function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    console.log('🔄 AuthGuard: useEffect triggered', { user: !!user, loading })
    if (!loading && !user) {
      console.log('🔄 AuthGuard: No user and not loading, redirecting to /auth')
      router.push('/auth')
    }
  }, [user, loading, router])

  // Show loading while checking authentication
  if (loading) {
    console.log('🔄 AuthGuard: Showing loading spinner')
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
    console.log('🔄 AuthGuard: No user authenticated')
    if (fallback) {
      console.log('🔄 AuthGuard: Showing fallback')
      return <>{fallback}</>
    }
    // Return loading state while redirecting
    console.log('🔄 AuthGuard: Showing redirect loading state')
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
  console.log('🔄 AuthGuard: User authenticated, showing children')
  return <>{children}</>
} 