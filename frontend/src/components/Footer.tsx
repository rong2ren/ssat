import { Mail } from 'lucide-react'

interface FooterProps {
  showChinese?: boolean
}

export default function Footer({ showChinese = false }: FooterProps) {
  const translations = {
    'Support': '支持',
    'Email us at': '发送邮件至'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  return (
    <footer className="bg-gray-50 border-t border-gray-200 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
          <Mail className="h-4 w-4" />
          <span>
            {t('Email us at')}:{' '}
            <a 
              href="mailto:ssat@schoolbase.org" 
              className="text-blue-600 hover:text-blue-800 underline"
            >
              ssat@schoolbase.org
            </a>
          </span>
        </div>
      </div>
    </footer>
  )
} 