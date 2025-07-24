'use client'

import React, { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

interface ForgotPasswordFormProps {
  onSwitchToLogin: () => void
  showChinese?: boolean
}

export default function ForgotPasswordForm({ onSwitchToLogin, showChinese = false }: ForgotPasswordFormProps) {
  const { forgotPassword, loading, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [emailSent, setEmailSent] = useState(false)

  // UI translations
  const translations = {
    'Check Your Email': '查看您的邮箱',
    'Password reset email sent to': '密码重置邮件已发送至',
    'We\'ve sent you a password reset link. Please check your email and click the link to reset your password.': '我们已向您发送密码重置链接。请查看您的邮箱并点击链接重置密码。',
    'Back to Login': '返回登录',
    'Forgot Password': '忘记密码',
    'Email': '邮箱',
    'Enter your email': '请输入您的邮箱',
    'Send Reset Link': '发送重置链接',
    'Sending...': '发送中...'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    const success = await forgotPassword(email)
    if (success) {
      setEmailSent(true)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value)
  }

  if (emailSent) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
          <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
            {t('Check Your Email')}
          </h2>
          
          <div className="text-center space-y-4">
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              {t('Password reset email sent to')} {email}
            </div>
            
            <p className="text-gray-600">
              {t('We\'ve sent you a password reset link. Please check your email and click the link to reset your password.')}
            </p>
            
            <button
              onClick={onSwitchToLogin}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              {t('Back to Login')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
          {t('Forgot Password')}
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              {t('Email')}
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t('Enter your email')}
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t('Sending...') : t('Send Reset Link')}
          </button>
          
          <div className="text-center">
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="text-blue-600 hover:text-blue-800 underline text-sm"
            >
              {t('Back to Login')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
} 