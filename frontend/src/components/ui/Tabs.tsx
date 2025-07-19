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
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1">
        <nav className="flex space-x-1" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={clsx(
                'group inline-flex items-center py-3 px-6 rounded-lg font-semibold text-sm transition-all duration-200 cursor-pointer flex-1 justify-center',
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              )}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.icon && (
                <span className={clsx(
                  'mr-2',
                  activeTab === tab.id ? 'text-white' : 'text-gray-400 group-hover:text-gray-600'
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
      <div className="mt-6">
        {tabs.map((tab) => (
          activeTab === tab.id && tab.description && (
            <div key={tab.id} className="text-center">
              <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
                {tab.description}
              </p>
            </div>
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