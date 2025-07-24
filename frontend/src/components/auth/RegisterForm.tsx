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
    'Resend confirmation email': '重新发送确认邮件'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    const success = await register(formData)
    if (success) {
      // Registration successful, user will be redirected or state will update
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
        
        <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
            {error.includes('check your email') && (
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
      </div>
    </div>
  )
} 