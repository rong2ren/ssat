import React from 'react'

interface ProgressProps {
  value: number
  max?: number
  className?: string
  indicatorClassName?: string
}

export function Progress({ 
  value, 
  max = 100, 
  className = '', 
  indicatorClassName = 'bg-blue-500' 
}: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  
  return (
    <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${className}`}>
      <div 
        className={`h-full transition-all duration-300 ease-out ${indicatorClassName}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
} 