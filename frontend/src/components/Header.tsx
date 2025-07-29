'use client'

import React, { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { BookOpen, Home, Globe, LogIn, Target } from 'lucide-react'
import { Button } from './ui/Button'
import { useAuth } from '@/contexts/AuthContext'
import UserProfile from './auth/UserProfile'

interface HeaderProps {
  showChinese?: boolean
  onLanguageToggle?: () => void
}

function HeaderComponent({ showChinese = false, onLanguageToggle }: HeaderProps) {
  const pathname = usePathname()
  const { user, loading } = useAuth()
  
  // Debug logging for auth state changes
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔍 Header: Auth state changed', { 
        hasUser: !!user, 
        loading,
        userId: user?.id 
      })
    }
  }, [user, loading])

  // UI translations
  const translations = {
    'SmartSSAT': 'SmartSSAT',
    'AI-Powered SSAT Practice Platform': 'AI智能驱动的 SSAT 练习平台',
    'Home': '首页',
    'Single Section': '单项练习',
    'Full Test': '完整测试',
    'Admin': '管理员',
    'Profile': '个人资料',
    'Sign Out': '退出登录',
    'Sign In': '登录',
    'Register': '注册'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const isActive = (path: string) => pathname === path

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <Link href="/" className="flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity min-w-0">
            <div className="bg-blue-600 p-2 rounded-lg flex-shrink-0">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-base sm:text-xl font-bold text-gray-900 truncate">{t('SmartSSAT')}</h1>
              <p className="text-xs text-gray-500 hidden sm:block">{t('AI-Powered SSAT Practice Platform')}</p>
            </div>
          </Link>
          
          {/* Navigation and Actions */}
          <div className="flex items-center space-x-1 sm:space-x-2 lg:space-x-4">
            {/* Navigation Links - Icons only on mobile */}
            <nav className="flex space-x-0.5 sm:space-x-2 lg:space-x-4">
              <Link
                href="/"
                className={`flex items-center justify-center p-1.5 sm:p-2 rounded-md transition-colors ${
                  isActive('/') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Home className="h-4 w-4" />
                <span className="hidden lg:inline ml-2 text-sm font-medium">{t('Home')}</span>
              </Link>
              
              <Link
                href="/custom-section"
                className={`flex items-center justify-center p-1.5 sm:p-2 rounded-md transition-colors ${
                  isActive('/custom-section') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Target className="h-4 w-4" />
                <span className="hidden lg:inline ml-2 text-sm font-medium">{t('Single Section')}</span>
              </Link>
              
              <Link
                href="/full-test"
                className={`flex items-center justify-center p-1.5 sm:p-2 rounded-md transition-colors ${
                  isActive('/full-test') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                <span className="hidden lg:inline ml-2 text-sm font-medium">{t('Full Test')}</span>
              </Link>
            </nav>

            {/* Language Toggle - Compact on mobile */}
            {onLanguageToggle && (
              <Button
                variant="outline"
                size="sm"
                onClick={onLanguageToggle}
                className="flex items-center justify-center px-1.5 sm:px-3 h-8 sm:h-9 min-w-0"
                title={showChinese ? 'Switch to English' : '切换到中文'}
              >
                <Globe className="h-3 w-3 sm:h-4 sm:w-4 flex-shrink-0" />
                <span className="text-xs sm:text-sm font-medium truncate hidden sm:inline sm:ml-1">
                  {showChinese ? 'EN' : '中文'}
                </span>
              </Button>
            )}

            {/* Authentication */}
            {user ? (
              <UserProfile showChinese={showChinese} />
            ) : !loading ? (
              <Link href="/auth">
                <Button
                  variant="default"
                  size="sm"
                  className="flex items-center space-x-1 sm:space-x-2 px-1.5 sm:px-3 h-8 sm:h-9"
                >
                  <LogIn className="h-3 w-3 sm:h-4 sm:w-4" />
                  <span className="text-xs sm:text-sm hidden sm:inline">{t('Sign In')}</span>
                </Button>
              </Link>
            ) : (
              // Show loading state while checking authentication
              <div className="flex items-center space-x-1 sm:space-x-2 px-1.5 sm:px-3 h-8 sm:h-9">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export const Header = React.memo(HeaderComponent)