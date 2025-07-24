'use client'

import React, { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { UserLogin } from '@/types/api'

interface LoginFormProps {
  onSwitchToRegister: () => void
  onSwitchToForgotPassword: () => void
  showChinese?: boolean
}

export default function LoginForm({ onSwitchToRegister, onSwitchToForgotPassword, showChinese = false }: LoginFormProps) {
  const { login, loading, error, clearError } = useAuth()
  const [formData, setFormData] = useState<UserLogin>({
    email: '',
    password: ''
  })

  // UI translations
  const translations = {
    'Welcome Back': '欢迎回来',
    'Email': '邮箱',
    'Enter your email': '请输入您的邮箱',
    'Password': '密码',
    'Enter your password': '请输入您的密码',
    'Forgot Password?': '忘记密码？',
    'Sign In': '登录',
    'Signing in...': '登录中...',
    'Don\'t have an account?': '没有账户？',
    'Sign up here': '点击这里注册'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    const success = await login(formData)
    if (success) {
      // Login successful, user will be redirected or state will update
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
          {t('Welcome Back')}
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
              {t('Password')}
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={t('Enter your password')}
            />
            <div className="text-right mt-1">
              <button
                type="button"
                onClick={onSwitchToForgotPassword}
                className="text-blue-600 hover:text-blue-800 underline text-sm"
              >
                {t('Forgot Password?')}
              </button>
            </div>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? t('Signing in...') : t('Sign In')}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            {t('Don\'t have an account?')}{' '}
            <button
              onClick={onSwitchToRegister}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              {t('Sign up here')}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
} 