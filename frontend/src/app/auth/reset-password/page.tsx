'use client'

import React from 'react'
import ResetPasswordForm from '@/components/auth/ResetPasswordForm'

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            SSAT Practice Platform
          </h1>
          <p className="text-gray-600">
            Reset your password
          </p>
        </div>

        <ResetPasswordForm />
      </div>
    </div>
  )
} 