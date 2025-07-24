'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { UserProfile, UserLogin, UserRegister, UserProfileUpdate, UserContentStats, AuthResponse, ResetPasswordRequest } from '@/types/api'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'

            interface AuthContextType {
              user: UserProfile | null
              loading: boolean
              error: string | null
              login: (credentials: UserLogin) => Promise<boolean>
              register: (userData: UserRegister) => Promise<boolean>
              resendConfirmation: (email: string) => Promise<boolean>
              forgotPassword: (email: string) => Promise<boolean>
              logout: () => Promise<void>
              updateProfile: (data: UserProfileUpdate) => Promise<boolean>
              getUserStats: () => Promise<UserContentStats | null>
              clearError: () => void
            }

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize auth state and listen for auth changes
  useEffect(() => {
    // console.log('🔄 AuthContext: useEffect started - initializing auth state')
    
    // Get initial session
    const getInitialSession = async () => {
      // console.log('🔄 AuthContext: getInitialSession started')
      const startTime = performance.now()
      
      const { data: { session } } = await supabase.auth.getSession()
              const sessionTime = performance.now() - startTime
        // console.log(`🔄 AuthContext: getSession completed in ${sessionTime.toFixed(2)}ms`, { hasSession: !!session, hasUser: !!session?.user })
      
      if (session?.user) {
                  // console.log('🔄 AuthContext: Session found, calling fetchUserProfile')
          await fetchUserProfile(session)
        } else {
          // console.log('🔄 AuthContext: No session found, setting loading to false')
          setLoading(false)
        }
    }

    getInitialSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        const eventTime = performance.now()
        // console.log(`🔄 AuthContext: Auth state changed at ${eventTime.toFixed(2)}ms:`, event, session?.user?.email)
        
        if (event === 'SIGNED_IN' && session?.user) {
          // console.log('🔄 AuthContext: SIGNED_IN event, calling fetchUserProfile')
          await fetchUserProfile(session)
        } else if (event === 'SIGNED_OUT') {
          // console.log('🔄 AuthContext: SIGNED_OUT event, clearing user')
          setUser(null)
          setLoading(false)
        } else if (event === 'TOKEN_REFRESHED' && session?.user) {
          // console.log('🔄 AuthContext: TOKEN_REFRESHED event, calling fetchUserProfile')
          await fetchUserProfile(session)
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const fetchUserProfile = async (session: any) => {
    // console.log('🔄 AuthContext: fetchUserProfile started')
    const startTime = performance.now()
    
    try {
      if (!session?.user) {
        // console.log('🔄 AuthContext: No user in session, clearing state')
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
        created_at: session.user.created_at,
        updated_at: session.user.updated_at || session.user.created_at
      }
      
      // console.log('🔄 AuthContext: Profile created, setting user state')
      setUser(profile)
      
      const profileTime = performance.now() - startTime
      // console.log(`🔄 AuthContext: fetchUserProfile completed in ${profileTime.toFixed(2)}ms`)
      
    } catch (err) {
      // console.error('🔄 AuthContext: Failed to create user profile from session:', err)
      await supabase.auth.signOut()
    } finally {
      // console.log('🔄 AuthContext: Setting loading to false')
      setLoading(false)
    }
  }

                const login = async (credentials: UserLogin): Promise<boolean> => {
                // console.log('🔄 AuthContext: login started')
                const startTime = performance.now()
                
                try {
                  setLoading(true)
                  setError(null)

                  // Use Supabase auth directly
                  // console.log('🔄 AuthContext: Calling supabase.auth.signInWithPassword...')
                  const authStartTime = performance.now()
                  
                  // Add timeout for slow connections
                  const timeoutPromise = new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Authentication timeout')), 30000)
                  )
                  
                  const authPromise = supabase.auth.signInWithPassword({
                    email: credentials.email,
                    password: credentials.password
                  })
                  
                  const { data, error } = await Promise.race([authPromise, timeoutPromise]) as any

                  const authTime = performance.now() - authStartTime
                  const totalTime = performance.now() - startTime
                  // console.log(`🔄 AuthContext: signInWithPassword completed in ${authTime.toFixed(2)}ms (total: ${totalTime.toFixed(2)}ms)`, { hasError: !!error, hasUser: !!data.user, hasSession: !!data.session })

                  if (error) {
                    // console.log('🔄 AuthContext: Login error:', error.message)
                    setError(error.message)
                    return false
                  }

                  if (data.user && data.session) {
                    // console.log('🔄 AuthContext: Login successful, profile will be set by onAuthStateChange')
                    
                    // console.log(`🔄 AuthContext: login completed in ${totalTime.toFixed(2)}ms`)
                    return true
                  } else {
                    // console.log('🔄 AuthContext: Login failed - no user or session')
                    setError('Login failed')
                    return false
                  }
                } catch (err) {
                  // console.error('🔄 AuthContext: Login exception:', err)
                  setError('Network error. Please try again.')
                  return false
                } finally {
                  // console.log('🔄 AuthContext: Login finally block - setting loading to false')
                  setLoading(false)
                }
              }

              const resendConfirmation = async (email: string): Promise<boolean> => {
                try {
                  setLoading(true)
                  setError(null)

                  const { error } = await supabase.auth.resend({
                    type: 'signup',
                    email: email
                  })

                  if (error) {
                    setError(error.message)
                    return false
                  }

                  setError('Confirmation email sent. Please check your inbox.')
                  return true
                } catch (err) {
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
                } catch (err) {
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

                  if (error) {
                    setError(error.message)
                    return false
                  }

                  if (data.user) {
                    if (data.session) {
                      // Email already confirmed, user logged in
                      await fetchUserProfile(data.session)
                      return true
                    } else {
                      // Email confirmation required
                      setError('Please check your email to confirm your account before logging in.')
                      return false
                    }
                  } else {
                    setError('Registration failed')
                    return false
                  }
                } catch (err) {
                  setError('Network error. Please try again.')
                  return false
                } finally {
                  setLoading(false)
                }
              }

  const logout = async (): Promise<void> => {
    try {
      await supabase.auth.signOut()
    } catch (err) {
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
    } catch (err) {
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
    } catch (err) {
      // console.error('Failed to get user stats:', err)
      return null
    }
  }

  const clearError = () => {
    setError(null)
  }

  // Memoize the context value to prevent unnecessary re-renders
  const value: AuthContextType = React.useMemo(() => ({
    user,
    loading,
    error,
    login,
    register,
    resendConfirmation,
    forgotPassword,
    logout,
    updateProfile,
    getUserStats,
    clearError
  }), [user, loading, error])

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