import { Mail, MessageCircle } from 'lucide-react'

interface FooterProps {
  showChinese?: boolean
}

export default function Footer({ showChinese = false }: FooterProps) {
  const translations = {
    'Support': '支持',
    'Email': '邮箱',
    'WeChat': '微信',
    'Contact us': '联系我们'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  return (
    <footer className="bg-gray-50 border-t border-gray-200 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-6 text-sm text-gray-600">
          <div className="flex items-center space-x-2">
            <Mail className="h-4 w-4" />
            <span>
              {t('Email')}:{' '}
              <a 
                href="mailto:ssat@schoolbase.org" 
                className="text-blue-600 hover:text-blue-800 underline"
              >
                ssat@schoolbase.org
              </a>
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <MessageCircle className="h-4 w-4" />
            <span>
              {t('WeChat')}:{' '}
              <span className="text-blue-600 font-medium">
                school_base
              </span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
} 