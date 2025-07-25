'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getAuthHeaders } from '@/utils/auth'
import { useRouter } from 'next/navigation'

interface UserData {
  id: string
  email: string
  role: string
  created_at: string
  last_sign_in_at: string | null
  limits: {
    quantitative: number
    analogy: number
    synonyms: number
    reading_passages: number
    writing: number
  }
  usage: {
    quantitative_generated: number
    analogy_generated: number
    synonyms_generated: number
    reading_passages_generated: number
    writing_generated: number
    last_reset_date: string | null
  }
}

export default function AdminPage() {
  const [users, setUsers] = useState<UserData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingRole, setUpdatingRole] = useState<string | null>(null)
  const { user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    const checkAdminAndFetchUsers = async () => {
      if (!user) {
        router.push('/auth')
        return
      }

      try {
        setLoading(true)
        setError(null)

        const headers = await getAuthHeaders()
        const response = await fetch('/api/admin/users', {
          headers
        })

        if (response.status === 403) {
          setError('Access denied. Admin privileges required.')
          return
        }

        if (!response.ok) {
          throw new Error('Failed to fetch users')
        }

        const data = await response.json()
        if (data.success && data.data) {
          setUsers(data.data)
        } else {
          throw new Error('Invalid response format')
        }
      } catch (err) {
        console.error('Error fetching users:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    checkAdminAndFetchUsers()
  }, [user, router])

  const updateUserRole = async (userId: string, newRole: string) => {
    try {
      setUpdatingRole(userId)
      const headers = await getAuthHeaders()
      
      const response = await fetch(`/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role: newRole })
      })

      if (!response.ok) {
        throw new Error('Failed to update user role')
      }

      // Refresh the users list
      const usersResponse = await fetch('/api/admin/users', { headers })
      const usersData = await usersResponse.json()
      if (usersData.success && usersData.data) {
        setUsers(usersData.data)
      }
    } catch (err) {
      console.error('Error updating user role:', err)
      alert('Failed to update user role')
    } finally {
      setUpdatingRole(null)
    }
  }

  const formatLimit = (limit: number) => {
    return limit === -1 ? '∞' : limit.toString()
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString()
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800'
      case 'premium': return 'bg-blue-100 text-blue-800'
      case 'free': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="text-lg">Loading users...</div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="text-red-600 text-lg">{error}</div>
            <button 
              onClick={() => router.push('/')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="mt-2 text-gray-600">Manage users and their daily limits</p>
        </div>

        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Users ({users.length})
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Limits
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usage Today
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((userData) => (
                  <tr key={userData.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {userData.email}
                        </div>
                        <div className="text-sm text-gray-500">
                          Created: {formatDate(userData.created_at)}
                        </div>
                        <div className="text-sm text-gray-500">
                          Last login: {formatDate(userData.last_sign_in_at)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleColor(userData.role)}`}>
                        {userData.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="space-y-1">
                        <div>Math: {formatLimit(userData.limits.quantitative)}</div>
                        <div>Analogy: {formatLimit(userData.limits.analogy)}</div>
                        <div>Synonyms: {formatLimit(userData.limits.synonyms)}</div>
                        <div>Reading: {formatLimit(userData.limits.reading_passages)}</div>
                        <div>Writing: {formatLimit(userData.limits.writing)}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div className="space-y-1">
                        <div>Math: {userData.usage.quantitative_generated}</div>
                        <div>Analogy: {userData.usage.analogy_generated}</div>
                        <div>Synonyms: {userData.usage.synonyms_generated}</div>
                        <div>Reading: {userData.usage.reading_passages_generated}</div>
                        <div>Writing: {userData.usage.writing_generated}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <select
                        value={userData.role}
                        onChange={(e) => updateUserRole(userData.id, e.target.value)}
                        disabled={updatingRole === userData.id}
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      >
                        <option value="free">Free</option>
                        <option value="premium">Premium</option>
                        <option value="admin">Admin</option>
                      </select>
                      {updatingRole === userData.id && (
                        <div className="mt-2 text-xs text-gray-500">Updating...</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
} 