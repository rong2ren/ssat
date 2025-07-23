'use client'

import React, { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { UserProfileUpdate, GradeLevel } from '@/types/api'
import { supabase } from '@/lib/supabase'

export default function UserProfile() {
  const { user, logout, updateProfile, loading, error, clearError } = useAuth()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [showProfile, setShowProfile] = useState(false)
  const [editing, setEditing] = useState(false)
  const [logoutLoading, setLogoutLoading] = useState(false)
  const [showResetPassword, setShowResetPassword] = useState(false)
  const [formData, setFormData] = useState<UserProfileUpdate>({
    full_name: user?.full_name || '',
    grade_level: user?.grade_level
  })
  const [newPassword, setNewPassword] = useState('')
  const [reauthenticating, setReauthenticating] = useState(false)

  const gradeLevels: GradeLevel[] = ['3rd', '4th', '5th', '6th', '7th', '8th']

  const handleLogout = async () => {
    setLogoutLoading(true)
    try {
      await logout()
      setShowProfile(false)
    } finally {
      setLogoutLoading(false)
    }
  }

  const handleEdit = () => {
    setFormData({
      full_name: user?.full_name || '',
      grade_level: user?.grade_level
    })
    setEditing(true)
    clearError()
  }

  const handleSave = async () => {
    const success = await updateProfile(formData)
    if (success) {
      setEditing(false)
    }
  }

  const handleCancel = () => {
    setEditing(false)
    clearError()
  }

  const handleResetPassword = () => {
    setShowResetPassword(true)
    clearError()
  }

  const handleCancelResetPassword = () => {
    setShowResetPassword(false)
    clearError()
    setSuccessMessage(null)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value === '' ? undefined : value
    }))
  }

  const handleResetPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewPassword(e.target.value)
  }

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setSuccessMessage(null)
    
    if (!newPassword.trim()) {
      setSuccessMessage('New password is required.')
      return
    }
    
    if (newPassword.length < 6) {
      setSuccessMessage('New password must be at least 6 characters long.')
      return
    }
    
    try {
      // Try to update password directly first
      const { error } = await supabase.auth.updateUser({
        password: newPassword
      })
      
      if (error) {
        // If update fails due to recent authentication requirement, 
        // we need to reauthenticate first
        if (error.message.includes('recently signed in') || error.message.includes('reauthenticate')) {
          setReauthenticating(true)
          
          // Send reauthentication nonce
          const { error: reauthError } = await supabase.auth.reauthenticate()
          
          if (reauthError) {
            setSuccessMessage('Failed to send reauthentication email. Please try again.')
            setReauthenticating(false)
            return
          }
          
          setSuccessMessage('Please check your email for a reauthentication code, then try again.')
          setReauthenticating(false)
          return
        }
        setSuccessMessage(error.message)
        return
      }

      setShowResetPassword(false)
      setNewPassword('')
      setSuccessMessage('Password updated successfully!')
    } catch (err) {
      setSuccessMessage('Failed to update password. Please try again.')
    }
  }

  if (!user) return null

  return (
    <div className="relative">
      {/* Profile Button */}
      <button
        onClick={() => setShowProfile(!showProfile)}
        className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md px-3 py-2"
      >
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-medium">
          {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
        </div>
        <span className="hidden md:block">
          {user.full_name || user.email}
        </span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Profile Dropdown */}
      {showProfile && (
        <div className="absolute right-0 mt-2 w-72 sm:w-80 bg-white rounded-md shadow-lg border border-gray-200 z-50">
          <div className="p-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white font-medium text-lg">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className="font-medium text-gray-900">
                  {user.full_name || 'No name set'}
                </h3>
                <p className="text-sm text-gray-500">{user.email}</p>
                {user.grade_level && (
                  <p className="text-sm text-gray-500">{user.grade_level} Grade</p>
                )}
              </div>
            </div>

            {editing ? (
              <div className="space-y-3">
                {error && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                    {error}
                  </div>
                )}
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    name="full_name"
                    value={formData.full_name || ''}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter your full name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Grade Level
                  </label>
                  <select
                    name="grade_level"
                    value={formData.grade_level || ''}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select grade level</option>
                    {gradeLevels.map(grade => (
                      <option key={grade} value={grade}>
                        {grade} Grade
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={handleSave}
                    disabled={loading}
                    className="flex-1 bg-blue-600 text-white py-2 px-3 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
                  >
                    {loading ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={handleCancel}
                    className="flex-1 bg-gray-300 text-gray-700 py-2 px-3 rounded-md hover:bg-gray-400 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : showResetPassword ? (
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900 mb-3">Reset Password</h4>
                {error && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                    {error}
                  </div>
                )}
                {successMessage && (
                  <div className={`px-3 py-2 rounded text-sm ${
                    successMessage.includes('successfully') 
                      ? 'bg-green-100 border border-green-400 text-green-700'
                      : 'bg-red-100 border border-red-400 text-red-700'
                  }`}>
                    {successMessage}
                  </div>
                )}
                
                <form onSubmit={handleResetPasswordSubmit} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      New Password
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={newPassword}
                      onChange={handleResetPasswordChange}
                      required
                      minLength={6}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter new password (min 6 characters)"
                    />
                  </div>

                  <div className="flex space-x-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-blue-600 text-white py-2 px-3 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
                    >
                      {loading ? 'Updating...' : 'Update Password'}
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelResetPassword}
                      className="flex-1 bg-gray-300 text-gray-700 py-2 px-3 rounded-md hover:bg-gray-400 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              <div className="space-y-2">
                <button
                  onClick={handleEdit}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  Edit Profile
                </button>
                <button
                  onClick={handleResetPassword}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
                >
                  Reset Password
                </button>
                <button
                  onClick={handleLogout}
                  disabled={logoutLoading}
                  className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-between"
                >
                  <span>Sign Out</span>
                  {logoutLoading && (
                    <svg className="animate-spin h-4 w-4 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {showProfile && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowProfile(false)}
        />
      )}
    </div>
  )
} 