'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib'

interface ResetPasswordFormProps {
  showChinese?: boolean
}

export default function ResetPasswordForm({ showChinese = false }: ResetPasswordFormProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [passwordReset, setPasswordReset] = useState(false)
  const [password, setPassword] = useState('')
  const router = useRouter()

  // UI translations
  const translations = {
    'Password Reset Successful': '密码重置成功',
    'Your password has been successfully reset. You are now logged in with your new password.': '您的密码已成功重置。您现在可以使用新密码登录。',
    'Go to Dashboard': '前往主页',
    'Reset Your Password': '重置您的密码',
    'Enter your new password below.': '请在下方输入您的新密码。',
    'New Password': '新密码',
    'Enter new password (min 6 characters)': '输入新密码（至少6个字符）',
    'Reset Password': '重置密码',
    'Resetting Password...': '重置密码中...',
    'Back to Login': '返回登录'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  useEffect(() => {
    // Extract parameters from URL hash fragments
    const hash = window.location.hash.substring(1) // Remove the # symbol
    const params = new URLSearchParams(hash)
    
    const accessToken = params.get('access_token')
    const expiresAt = params.get('expires_at')
    const expiresIn = params.get('expires_in')
    const refreshToken = params.get('refresh_token')
    const tokenType = params.get('token_type')
    const type = params.get('type')
    
    console.log('Reset password hash params:', { 
      accessToken: accessToken ? '[hidden]' : null,
      expiresAt, 
      expiresIn, 
      refreshToken: refreshToken ? '[hidden]' : null,
      tokenType, 
      type 
    })
    
    // Check if we have the necessary parameters for recovery
    if (accessToken && type === 'recovery') {
      console.log('Valid recovery token found')
      // The session should be established automatically by Supabase
    } else {
      console.log('Missing or invalid recovery parameters')
      setError('Invalid or expired reset link. Please request a new one.')
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      // First, verify we have a valid recovery session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession()
      
      if (sessionError) {
        console.error('Session error:', sessionError)
        setError('Invalid or expired reset link. Please request a new one.')
        return
      }
      
      if (!session) {
        console.error('No session found')
        setError('Invalid or expired reset link. Please request a new one.')
        return
      }
      
      // Verify this is a recovery session
      const user = session.user
      if (!user.app_metadata || user.app_metadata.provider !== 'email') {
        console.error('Invalid session type for password reset')
        setError('Invalid recovery session. Please request a new reset link.')
        return
      }
      
      // Check if user is in recovery mode
      if (!user.app_metadata.providers || !user.app_metadata.providers.includes('email')) {
        console.error('User not in recovery mode')
        setError('Invalid recovery session. Please request a new reset link.')
        return
      }
      
      console.log('Valid recovery session confirmed, updating password...')
      
      // Update the password
      const { error } = await supabase.auth.updateUser({
        password: password
      })
      
      if (error) {
        console.error('Password update error:', error)
        
        // Handle specific error cases
        if (error.message.includes('Invalid recovery token')) {
          setError('Invalid or expired reset link. Please request a new one.')
        } else if (error.message.includes('User not found')) {
          setError('User account not found.')
        } else if (error.message.includes('Email not confirmed')) {
          setError('Please confirm your email address first.')
        } else {
          setError(error.message)
        }
        return
      }
      
      console.log('Password updated successfully')
      setPasswordReset(true)
      
    } catch (err) {
      console.error('Password reset exception:', err)
      setError('Failed to reset password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (passwordReset) {
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">{t('Password Reset Successful')}</h2>
        <p className="text-gray-600 mb-4">
          {t('Your password has been successfully reset. You are now logged in with your new password.')}
        </p>
        <button
          onClick={() => router.push('/')}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
        >
          {t('Go to Dashboard')}
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">{t('Reset Your Password')}</h2>
      <p className="text-gray-600 mb-6">
        {t('Enter your new password below.')}
      </p>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
            {t('New Password')}
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={t('Enter new password (min 6 characters)')}
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? t('Resetting Password...') : t('Reset Password')}
        </button>
      </form>
      
      <div className="mt-4 text-center">
        <button
          onClick={() => router.push('/auth')}
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          {t('Back to Login')}
        </button>
      </div>
    </div>
  )
} 