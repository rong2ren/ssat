'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Globe, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'

interface LanguageOption {
  value: string
  label: string
  flag?: string
}

interface LanguageSelectorProps {
  value: string
  onChange: (value: string) => void
  options: LanguageOption[]
  className?: string
  size?: 'sm' | 'md'
}

export function LanguageSelector({ 
  value, 
  onChange, 
  options, 
  className,
  size = 'md'
}: LanguageSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const selectedOption = options.find(option => option.value === value)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const sizeClasses = {
    sm: 'h-8 px-1.5 sm:px-2 text-xs',
    md: 'h-9 px-2 sm:px-3 text-sm'
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4'
  }

  return (
    <div className={clsx('relative', className)} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center space-x-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
          sizeClasses[size]
        )}
      >
        <Globe className={clsx('text-gray-500 flex-shrink-0', iconSizes[size])} />
        <span className="text-gray-700 font-medium min-w-0 hidden sm:inline">
          {selectedOption?.label}
        </span>
        <ChevronDown 
          className={clsx(
            'text-gray-400 flex-shrink-0 transition-transform duration-200 hidden sm:block',
            isOpen ? 'rotate-180' : '',
            iconSizes[size]
          )} 
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-full min-w-[120px] bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value)
                setIsOpen(false)
              }}
              className={clsx(
                'w-full flex items-center space-x-2 px-3 py-2 text-left hover:bg-gray-50 transition-colors first:rounded-t-lg last:rounded-b-lg',
                value === option.value ? 'bg-blue-50 text-blue-700' : 'text-gray-700',
                sizeClasses[size]
              )}
            >
              <Globe className={clsx('text-gray-500 flex-shrink-0', iconSizes[size])} />
              <span className="font-medium">{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
