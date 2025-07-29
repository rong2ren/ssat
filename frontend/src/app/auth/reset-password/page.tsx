'use client'

import React from 'react'
import { usePreferences } from '@/contexts/AppStateContext'
import ResetPasswordForm from '@/components/auth/ResetPasswordForm'
import { Globe } from 'lucide-react'

export default function ResetPasswordPage() {
  const { showChinese, dispatch } = usePreferences()
  
  // UI translations
  const translations = {
    'SmartSSAT': 'SmartSSAT',
    'Reset your password': '重置您的密码',
    'Enter your email address and we\'ll send you a link to reset your password.': '请输入您的邮箱地址，我们将发送重置密码链接给您。',
    'Email': '邮箱',
    'Send reset link': '发送重置链接',
    'Back to sign in': '返回登录',
    'Enter your email': '请输入您的邮箱',
    'Password reset email sent. Please check your inbox.': '密码重置邮件已发送，请查看您的收件箱。',
    'Network error. Please try again.': '网络错误，请重试。'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

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
            {t('SmartSSAT')}
          </h1>
          <p className="text-gray-600">
            {t('Reset your password')}
          </p>
        </div>

        <ResetPasswordForm showChinese={showChinese} />
      </div>
    </div>
  )
} 