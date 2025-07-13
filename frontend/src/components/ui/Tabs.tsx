'use client'

import React, { useState } from 'react'
import { clsx } from 'clsx'

interface TabItem {
  id: string
  label: string
  icon?: React.ReactNode
  description?: string
}

interface TabsProps {
  tabs: TabItem[]
  defaultTab?: string
  onTabChange?: (tabId: string) => void
  className?: string
}

export function Tabs({ tabs, defaultTab, onTabChange, className }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id)

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId)
    onTabChange?.(tabId)
  }

  return (
    <div className={clsx('w-full', className)}>
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={clsx(
                'group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors',
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.icon && (
                <span className={clsx(
                  'mr-2',
                  activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                )}>
                  {tab.icon}
                </span>
              )}
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>
      
      {/* Tab descriptions */}
      <div className="mt-4">
        {tabs.map((tab) => (
          activeTab === tab.id && tab.description && (
            <p key={tab.id} className="text-sm text-gray-600 mb-6">
              {tab.description}
            </p>
          )
        ))}
      </div>
    </div>
  )
}

interface TabContentProps {
  activeTab: string
  tabId: string
  children: React.ReactNode
  className?: string
}

export function TabContent({ activeTab, tabId, children, className }: TabContentProps) {
  if (activeTab !== tabId) return null
  
  return (
    <div className={clsx('mt-6', className)}>
      {children}
    </div>
  )
}