'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { BookOpen, FileText, Home, Globe } from 'lucide-react'
import { Button } from './ui/Button'

interface HeaderProps {
  showChinese?: boolean
  onLanguageToggle?: () => void
}

export function Header({ showChinese = false, onLanguageToggle }: HeaderProps) {
  const pathname = usePathname()

  // UI translations
  const translations = {
    'SSAT Practice': 'SSAT 练习',
    'AI-Powered Question Generator': 'AI驱动的题目生成器',
    'Home': '首页',
    'Custom Section': '自定义练习',
    'Full Test': '完整测试'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const isActive = (path: string) => pathname === path

  // Use responsive classes with hydration-safe approach
  const containerClasses = "max-w-7xl mx-auto px-3 sm:px-4 lg:px-8"
  const headerClasses = "flex justify-between items-center h-16 sm:h-16"
  const logoClasses = "flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity"
  const iconClasses = "h-6 w-6 sm:h-6 sm:w-6 text-white"
  const navClasses = "flex space-x-1 sm:space-x-6"
  const linkClasses = "flex items-center justify-center space-x-1 sm:space-x-2 px-3 sm:px-3 py-2 rounded-md text-xs sm:text-sm font-medium min-w-[44px] sm:min-w-0"
  const navIconClasses = "h-4 w-4 sm:h-4 sm:w-4"
  const buttonClasses = "flex items-center space-x-1 sm:space-x-2 px-2 sm:px-3"
  const buttonIconClasses = "h-3 w-3 sm:h-4 sm:w-4"
  const buttonTextClasses = "text-xs sm:text-sm"

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className={containerClasses}>
        <div className={headerClasses}>
          {/* Logo and Brand */}
          <Link href="/" className={logoClasses}>
            <div className="bg-blue-600 p-2 rounded-lg">
              <BookOpen className={iconClasses} />
            </div>
            <div className="min-w-0">
              <h1 className="text-base sm:text-xl font-bold text-gray-900 truncate">{t('SSAT Practice')}</h1>
              <p className="text-xs text-gray-500 hidden sm:block">{t('AI-Powered Question Generator')}</p>
            </div>
          </Link>
          
          {/* Navigation Links */}
          <div className="flex items-center space-x-2 sm:space-x-4">
            <nav className={navClasses}>
              <Link
                href="/"
                className={`${linkClasses} transition-colors ${
                  isActive('/') 
                    ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100'
                }`}
              >
                <Home className={navIconClasses} />
                <span className="hidden sm:inline">{t('Home')}</span>
              </Link>
              
              <Link
                href="/custom-section"
                className={`${linkClasses} transition-colors ${
                  isActive('/custom-section') 
                    ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100'
                }`}
              >
                <FileText className={navIconClasses} />
                <span className="hidden sm:inline">{t('Custom Section')}</span>
              </Link>
              
              <Link
                href="/full-test"
                className={`${linkClasses} transition-colors ${
                  isActive('/full-test') 
                    ? 'bg-blue-100 text-blue-700 border border-blue-200' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 active:bg-gray-100'
                }`}
              >
                <BookOpen className={navIconClasses} />
                <span className="hidden sm:inline">{t('Full Test')}</span>
              </Link>
            </nav>

            {/* Language Toggle */}
            {onLanguageToggle && (
              <Button
                variant="outline"
                size="sm"
                onClick={onLanguageToggle}
                className={buttonClasses}
              >
                <Globe className={buttonIconClasses} />
                <span className={buttonTextClasses}>{showChinese ? 'English' : '中文'}</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}