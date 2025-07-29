'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { UserProfile, UserLogin, UserRegister, UserProfileUpdate, UserContentStats } from '@/types/api'
import { supabase } from '../lib/supabase'
import { clearAllLimitsCache } from '@/components/DailyLimitsDisplay'

            interface AuthContextType {
              user: UserProfile | null
              loading: boolean
              error: string | null
              successMessage: string | null
              registrationSuccess: boolean
              login: (credentials: UserLogin) => Promise<boolean>
              register: (userData: UserRegister) => Promise<boolean>
              forgotPassword: (email: string) => Promise<boolean>
              logout: () => Promise<void>
              updateProfile: (data: UserProfileUpdate) => Promise<boolean>
              getUserStats: () => Promise<UserContentStats | null>
              clearError: () => void
              clearSuccessMessage: () => void
              clearRegistrationSuccess: () => void
            }

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [registrationSuccess, setRegistrationSuccess] = useState(false)

  // Initialize auth state and listen for auth changes
  useEffect(() => {
    
    // Get initial session
    const getInitialSession = async () => {
      
      const { data: { session } } = await supabase.auth.getSession()
      
      if (session?.user) {
        // Only treat as logged in if email is confirmed
        if (session.user.email_confirmed_at) {
          await fetchUserProfile(session)
        } else {
          // Email not confirmed - don't set user as logged in
          setUser(null)
          setLoading(false)
        }
      } else {
        setLoading(false)
      }
    }

    getInitialSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        
        if (event === 'SIGNED_IN' && session?.user) {
          // Only treat as successful login if email is confirmed
          if (session.user.email_confirmed_at) {
            await fetchUserProfile(session)
          } else {
            // Email not confirmed - don't set user as logged in
            setLoading(false)
          }
        } else if (event === 'SIGNED_OUT') {
          setUser(null)
          setLoading(false)
        } else if (event === 'TOKEN_REFRESHED' && session?.user) {
          await fetchUserProfile(session)
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const fetchUserProfile = async (session: any) => {
    
    try {
      if (!session?.user) {
        setUser(null)
        setLoading(false)
        return
      }

      // Extract user data directly from Supabase session (following NestJS pattern)
      const user_metadata = session.user.user_metadata || {}
      
      const profile: UserProfile = {
        id: session.user.id,
        email: session.user.email || '',
        full_name: user_metadata.full_name || null,
        grade_level: user_metadata.grade_level || null,
        role: user_metadata.role || 'free',
        created_at: session.user.created_at,
        updated_at: session.user.updated_at || session.user.created_at
      }
      
      setUser(profile)
      
    } catch {
      await supabase.auth.signOut()
    } finally {
      setLoading(false)
    }
  }

                const login = async (credentials: UserLogin): Promise<boolean> => {
                try {
                  setLoading(true)
                  setError(null)

                  // Use Supabase auth directly
                  
                  // Add timeout for slow connections
                  const timeoutPromise = new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Authentication timeout')), 30000)
                  )
                  
                  const authPromise = supabase.auth.signInWithPassword({
                    email: credentials.email,
                    password: credentials.password
                  })
                  
                  const { data, error } = await Promise.race([authPromise, timeoutPromise]) as any

                  if (error) {
                    setError(error.message)
                    return false
                  }

                  if (data.user && data.session) {
                    
                    return true
                  } else {
                    setError('Login failed')
                    return false
                  }
                } catch {
                  setError('Network error. Please try again.')
                  return false
                } finally {
                  setLoading(false)
                }
              }

              const forgotPassword = async (email: string): Promise<boolean> => {
                try {
                  setLoading(true)
                  setError(null)

                  const { error } = await supabase.auth.resetPasswordForEmail(email, {
                    redirectTo: `${window.location.origin}/auth/reset-password`
                  })

                  if (error) {
                    setError(error.message)
                    return false
                  }

                  setError('Password reset email sent. Please check your inbox.')
                  return true
                } catch {
                  setError('Network error. Please try again.')
                  return false
                } finally {
                  setLoading(false)
                }
              }



                const register = async (userData: UserRegister): Promise<boolean> => {
                try {
                  setLoading(true)
                  setError(null)
                  setRegistrationSuccess(false)

                  console.log('🔍 DEBUG: Starting registration for:', userData.email)

                  // Use Supabase auth directly
                  const { data, error } = await supabase.auth.signUp({
                    email: userData.email,
                    password: userData.password,
                    options: {
                      data: {
                        full_name: userData.full_name,
                        grade_level: userData.grade_level
                      }
                    }
                  })

                  console.log('🔍 DEBUG: Supabase signUp response:', { data, error })

                  if (error) {
                    console.log('🔍 DEBUG: Registration error:', error.message)
                    
                    // Provide user-friendly error messages
                    let userFriendlyError = error.message
                    
                    if (error.message.includes('Error sending confirmation email')) {
                      userFriendlyError = 'Unable to send verification email. Please try again in a few minutes or contact support.'
                    } else if (error.message.includes('rate limit')) {
                      userFriendlyError = 'Too many registration attempts. Please wait a few minutes before trying again.'
                    } else if (error.message.includes('network') || error.message.includes('timeout')) {
                      userFriendlyError = 'Network connection issue. Please check your internet connection and try again.'
                    } else if (error.message.includes('email')) {
                      userFriendlyError = 'Invalid email address. Please check your email and try again.'
                    } else if (error.message.includes('password')) {
                      userFriendlyError = 'Password is too weak. Please use a stronger password (at least 6 characters).'
                    }
                    
                    setError(userFriendlyError)
                    return false
                  }

                  if (data.user) {
                    console.log('🔍 DEBUG: User created successfully:', data.user.id)
                    console.log('🔍 DEBUG: Session exists:', !!data.session)
                    console.log('🔍 DEBUG: Email confirmed:', !!data.user.email_confirmed_at)
                    
                    if (data.session) {
                      // User is immediately signed in (email confirmation not required)
                      console.log('🔍 DEBUG: User immediately signed in')
                      await fetchUserProfile(data.session)
                      return true
                    } else {
                      // User created but email verification required
                      console.log('🔍 DEBUG: User created, email verification required')
                      // Don't set user as logged in - they need to verify email first
                      setUser(null)
                      setRegistrationSuccess(true)  // Set success state in AuthContext
                      return true  // Return true to show success message in UI
                    }
                  } else {
                    console.log('🔍 DEBUG: No user in response')
                    setError('Registration failed')
                    return false
                  }
                } catch (err) {
                  console.log('🔍 DEBUG: Registration exception:', err)
                  setError('Network error. Please try again.')
                  return false
                } finally {
                  setLoading(false)
                }
              }

  const logout = async (): Promise<void> => {
    try {
      await supabase.auth.signOut()
      
      // Clear all limits cache on logout
      clearAllLimitsCache()
    } catch {
      // console.error('Logout error:', err)
    } finally {
      setUser(null)
    }
  }

  const updateProfile = async (data: UserProfileUpdate): Promise<boolean> => {
    try {
      setLoading(true)
      setError(null)

      // Use Supabase Auth API directly (standard approach)
      const { data: result, error } = await supabase.auth.updateUser({
        data: {
          full_name: data.full_name,
          grade_level: data.grade_level
        }
      })

      if (error) {
        setError(error.message)
        return false
      }

      if (result.user) {
        // Update local state with new user data
        const updatedProfile: UserProfile = {
          id: result.user.id,
          email: result.user.email || '',
          full_name: result.user.user_metadata?.full_name,
          grade_level: result.user.user_metadata?.grade_level,
          created_at: result.user.created_at,
          updated_at: result.user.updated_at || result.user.created_at
        }
        setUser(updatedProfile)
        return true
      } else {
        setError('Profile update failed')
        return false
      }
    } catch {
      setError('Network error. Please try again.')
      return false
    } finally {
      setLoading(false)
    }
  }

  const getUserStats = async (): Promise<UserContentStats | null> => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        return null
      }

      const response = await fetch('/api/auth/stats', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        return data.stats || null
      }
      return null
    } catch {
      // console.error('Failed to get user stats:', err)
      return null
    }
  }

  const clearError = () => {
    setError(null)
  }

  const clearSuccessMessage = () => {
    setSuccessMessage(null)
  }

  const clearRegistrationSuccess = () => {
    setRegistrationSuccess(false)
  }

  // Memoize the context value to prevent unnecessary re-renders
  const value: AuthContextType = React.useMemo(() => ({
    user,
    loading,
    error,
    successMessage,
    registrationSuccess,
    login,
    register,
    forgotPassword,
    logout,
    updateProfile,
    getUserStats,
    clearError,
    clearSuccessMessage,
    clearRegistrationSuccess
  }), [user, loading, error, successMessage, registrationSuccess])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
} 