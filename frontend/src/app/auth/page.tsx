'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { usePreferences } from '@/contexts/AppStateContext'
import LoginForm from '@/components/auth/LoginForm'
import RegisterForm from '@/components/auth/RegisterForm'
import ForgotPasswordForm from '@/components/auth/ForgotPasswordForm'
import { Globe } from 'lucide-react'

type AuthMode = 'login' | 'register' | 'forgot-password'

export default function AuthPage() {
  const [mode, setMode] = useState<AuthMode>('login')
  const { user, loading, clearError } = useAuth()
  const { showChinese, dispatch } = usePreferences()
  const router = useRouter()

  // UI translations
  const translations = {
    'SSAT Practice Platform': 'SSAT练习平台',
    'Sign in to generate personalized SSAT practice questions': '登录即可获取个性化SSAT备考练习',
    'Loading...': '加载中...'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

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
          <p className="mt-4 text-gray-600">{t('Loading...')}</p>
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
      {/* Language Toggle Button */}
      <div className="absolute top-4 right-4">
        <button
          onClick={() => dispatch({ type: 'SET_SHOW_CHINESE', payload: !showChinese })}
          className="flex items-center space-x-2 px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 transition-colors"
        >
          <Globe className="h-4 w-4" />
          <span className="text-sm">{showChinese ? 'EN' : '中文'}</span>
        </button>
      </div>
      
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {t('SSAT Practice Platform')}
          </h1>
          <p className="text-gray-600">
            {t('Sign in to generate personalized SSAT practice questions')}
          </p>
        </div>

        {mode === 'login' ? (
          <LoginForm 
            onSwitchToRegister={() => setMode('register')} 
            onSwitchToForgotPassword={() => setMode('forgot-password')}
            showChinese={showChinese}
          />
        ) : mode === 'register' ? (
          <RegisterForm onSwitchToLogin={() => setMode('login')} showChinese={showChinese} />
        ) : (
          <ForgotPasswordForm onSwitchToLogin={() => setMode('login')} showChinese={showChinese} />
        )}
      </div>
    </div>
  )
} 