'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import LoginForm from '@/components/auth/LoginForm'
import RegisterForm from '@/components/auth/RegisterForm'
import ForgotPasswordForm from '@/components/auth/ForgotPasswordForm'

type AuthMode = 'login' | 'register' | 'forgot-password'

export default function AuthPage() {
  const [mode, setMode] = useState<AuthMode>('login')
  const { user, loading, clearError } = useAuth()
  const router = useRouter()

  // Clear any lingering error messages when component mounts
  useEffect(() => {
    clearError()
  }, [clearError])

  // Redirect if user is already authenticated
  useEffect(() => {
    if (user && !loading) {
      router.push('/')
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

  // If user is authenticated, don't show auth page
  if (user) {
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            SSAT Practice Platform
          </h1>
          <p className="text-gray-600">
            Sign in to generate personalized SSAT practice questions
          </p>
        </div>

        {mode === 'login' ? (
          <LoginForm 
            onSwitchToRegister={() => setMode('register')} 
            onSwitchToForgotPassword={() => setMode('forgot-password')} 
          />
        ) : mode === 'register' ? (
          <RegisterForm onSwitchToLogin={() => setMode('login')} />
        ) : (
          <ForgotPasswordForm onSwitchToLogin={() => setMode('login')} />
        )}
      </div>
    </div>
  )
} 