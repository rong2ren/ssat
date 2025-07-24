'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { BookOpen, FileText, Home, Globe, LogIn, Target } from 'lucide-react'
import { Button } from './ui/Button'
import { useAuth } from '@/contexts/AuthContext'
import UserProfile from './auth/UserProfile'

interface HeaderProps {
  showChinese?: boolean
  onLanguageToggle?: () => void
}

export function Header({ showChinese = false, onLanguageToggle }: HeaderProps) {
  const pathname = usePathname()
  const { user, loading } = useAuth()
  // console.log('🔄 Header: Component rendering', { user: !!user, loading })

  // UI translations
  const translations = {
    'SSAT Practice': 'SSAT 练习',
    'AI-Powered Question Generator': 'AI驱动的题目生成器',
    'Home': '首页',
    'Custom Section': '自定义练习',
    'Full Test': '完整测试',
    'Sign In': '登录'
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
              <h1 className="text-base sm:text-xl font-bold text-gray-900 truncate">{t('SSAT Practice')}</h1>
              <p className="text-xs text-gray-500 hidden sm:block">{t('AI-Powered Question Generator')}</p>
            </div>
          </Link>
          
          {/* Navigation and Actions */}
          <div className="flex items-center space-x-1 sm:space-x-2 lg:space-x-4">
            {/* Navigation Links - Icons only on mobile */}
            <nav className="flex space-x-1 sm:space-x-2 lg:space-x-4">
              <Link
                href="/"
                className={`flex items-center justify-center p-2 rounded-md transition-colors ${
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
                className={`flex items-center justify-center p-2 rounded-md transition-colors ${
                  isActive('/custom-section') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Target className="h-4 w-4" />
                <span className="hidden lg:inline ml-2 text-sm font-medium">{t('Custom Section')}</span>
              </Link>
              
              <Link
                href="/full-test"
                className={`flex items-center justify-center p-2 rounded-md transition-colors ${
                  isActive('/full-test') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                <span className="hidden lg:inline ml-2 text-sm font-medium">{t('Full Test')}</span>
              </Link>
            </nav>

            {/* Language Toggle - Smaller on mobile */}
            {onLanguageToggle && (
              <Button
                variant="outline"
                size="sm"
                onClick={onLanguageToggle}
                className="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 h-8 sm:h-9"
              >
                <Globe className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">{showChinese ? 'EN' : '中文'}</span>
              </Button>
            )}

            {/* Authentication */}
            {!loading && (
              <>
                {user ? (
                  <UserProfile />
                ) : (
                  <Link href="/auth">
                    <Button
                      variant="default"
                      size="sm"
                      className="flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3 h-8 sm:h-9"
                    >
                      <LogIn className="h-3 w-3 sm:h-4 sm:w-4" />
                      <span className="text-xs sm:text-sm">{t('Sign In')}</span>
                    </Button>
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}