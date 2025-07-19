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

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <Link href="/" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
            <div className="bg-blue-600 p-2 rounded-lg">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{t('SSAT Practice')}</h1>
              <p className="text-xs text-gray-500">{t('AI-Powered Question Generator')}</p>
            </div>
          </Link>
          
          {/* Navigation Links */}
          <div className="flex items-center space-x-4">
            <nav className="flex space-x-6">
              <Link
                href="/"
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Home className="h-4 w-4" />
                <span>{t('Home')}</span>
              </Link>
              
              <Link
                href="/custom-section"
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/custom-section') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <FileText className="h-4 w-4" />
                <span>{t('Custom Section')}</span>
              </Link>
              
              <Link
                href="/full-test"
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/full-test') 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                <span>{t('Full Test')}</span>
              </Link>
            </nav>

            {/* Language Toggle */}
            {onLanguageToggle && (
              <Button
                variant="outline"
                size="sm"
                onClick={onLanguageToggle}
                className="flex items-center space-x-2"
              >
                <Globe className="h-4 w-4" />
                <span>{showChinese ? 'English' : '中文'}</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}