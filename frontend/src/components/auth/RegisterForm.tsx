'use client'

import React, { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { UserRegister, GradeLevel } from '@/types/api'

interface RegisterFormProps {
  onSwitchToLogin: () => void
  showChinese?: boolean
}

export default function RegisterForm({ onSwitchToLogin, showChinese = false }: RegisterFormProps) {
  const { register, resendConfirmation, loading, error, clearError } = useAuth()
  const [formData, setFormData] = useState<UserRegister>({
    email: '',
    password: '',
    full_name: '',
    grade_level: undefined
  })
  const [registrationSuccess, setRegistrationSuccess] = useState(false)

  const gradeLevels: GradeLevel[] = ['3rd', '4th', '5th', '6th', '7th', '8th']

  // UI translations
  const translations = {
    'Create Account': '创建账户',
    'Email *': '邮箱 *',
    'Enter your email': '请输入您的邮箱',
    'Password *': '密码 *',
    'Enter your password (min 6 characters)': '请输入您的密码（至少6个字符）',
    'Full Name': '姓名',
    'Enter your full name': '请输入您的姓名',
    'Grade Level': '年级',
    'Select grade level': '选择年级',
    'Grade': '年级',
    'Creating account...': '创建账户中...',
    'Already have an account?': '已有账户？',
    'Sign in here': '在此登录',
    'Resend confirmation email': '重新发送确认邮件',
    'Account Created Successfully!': '账户创建成功！',
    'Please check your email to verify your account.': '请检查您的邮箱以验证账户。',
    'You will receive a verification email from our authentication service.': '您将收到来自我们认证服务的验证邮件。',
    'Click the link in the email to complete your registration.': '点击邮件中的链接完成注册。',
    'Note: The email may appear to be from "Supabase" - this is our secure authentication provider.': '注意：邮件可能显示来自"Supabase" - 这是我们安全的认证服务提供商。',
    'After verification, you can sign in with your email and password.': '验证后，您可以使用邮箱和密码登录。',
    'Create Another Account': '创建另一个账户',
    'Try Again': '重试'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setRegistrationSuccess(false)
    
    const success = await register(formData)
    
    if (success) {
      setRegistrationSuccess(true)
    } else {
      // Registration failed - error will be displayed by AuthContext
    }
  }

  const handleResendConfirmation = async () => {
    await resendConfirmation(formData.email)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value === '' ? undefined : value
    }))
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
          {t('Create Account')}
        </h2>
        
        {registrationSuccess ? (
          <div className="space-y-4">
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              <h3 className="font-semibold mb-2">{t('Account Created Successfully!')}</h3>
              <p className="mb-2">{t('Please check your email to verify your account.')}</p>
              <p className="mb-2">{t('You will receive a verification email from our authentication service.')}</p>
              <p className="mb-2">{t('Click the link in the email to complete your registration.')}</p>
              <p className="mb-3 text-sm bg-yellow-50 p-2 rounded border border-yellow-200">
                <strong>ℹ️ {t('Note: The email may appear to be from "Supabase" - this is our secure authentication provider.')}</strong>
              </p>
              <p className="mb-3">{t('After verification, you can sign in with your email and password.')}</p>
              <button
                type="button"
                onClick={handleResendConfirmation}
                className="text-blue-600 hover:text-blue-800 underline text-sm"
              >
                {t('Resend confirmation email')}
              </button>
            </div>
            <button
              type="button"
              onClick={() => {
                setRegistrationSuccess(false)
                setFormData({ email: '', password: '', full_name: '', grade_level: undefined })
              }}
              className="w-full bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
            >
              {t('Create Another Account')}
            </button>
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium">{error}</p>
                      {error.includes('verification email') && (
                        <div className="mt-2">
                          <button
                            type="button"
                            onClick={handleResendConfirmation}
                            className="text-blue-600 hover:text-blue-800 underline text-sm"
                          >
                            {t('Resend confirmation email')}
                          </button>
                        </div>
                      )}
                      {error.includes('Unable to send verification email') && (
                        <div className="mt-2">
                          <button
                            type="button"
                            onClick={() => {
                              clearError()
                              setRegistrationSuccess(false)
                            }}
                            className="text-blue-600 hover:text-blue-800 underline text-sm"
                          >
                            {t('Try Again')}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Email *')}
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('Enter your email')}
                />
              </div>
              
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Password *')}
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  minLength={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('Enter your password (min 6 characters)')}
                />
              </div>
              
              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Full Name')}
                </label>
                <input
                  type="text"
                  id="full_name"
                  name="full_name"
                  value={formData.full_name || ''}
                  onChange={handleChange}
                  maxLength={50}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('Enter your full name')}
                />
              </div>
              
              <div>
                <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Grade Level')}
                </label>
                <select
                  id="grade_level"
                  name="grade_level"
                  value={formData.grade_level || ''}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">{t('Select grade level')}</option>
                  {gradeLevels.map(grade => (
                    <option key={grade} value={grade}>
                      {grade} {t('Grade')}
                    </option>
                  ))}
                </select>
              </div>
              
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? t('Creating account...') : t('Create Account')}
              </button>
            </form>
            
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                {t('Already have an account?')}{' '}
                <button
                  onClick={onSwitchToLogin}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  {t('Sign in here')}
                </button>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
} 