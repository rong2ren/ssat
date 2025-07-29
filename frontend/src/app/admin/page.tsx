'use client'

import React, { useState } from 'react'
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
    synonym: number
    reading_passages: number
    writing: number
  }
  usage: {
    quantitative_generated: number
    analogy_generated: number
    synonym_generated: number
    reading_passages_generated: number
    writing_generated: number
    last_reset_date: string | null
  }
}

interface GenerationResponse {
  success: boolean
  message: string
  session_id: string
  generation_time_ms: number
  provider_used: string
  content: any
}

type AdminSection = 'generate' | 'complete-test' | 'users'

export default function AdminPage() {
  const [activeSection, setActiveSection] = useState<AdminSection>('generate')
  const [officialCounts, setOfficialCounts] = useState<any>(null)
  
  // Users management state
  const [users, setUsers] = useState<UserData[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersError, setUsersError] = useState<string | null>(null)
  const [updatingRole, setUpdatingRole] = useState<string | null>(null)
  
  // Generation form state
  const [generationForm, setGenerationForm] = useState({
    question_type: 'quantitative' as 'quantitative' | 'reading' | 'analogy' | 'synonym' | 'writing',
    difficulty: 'Medium' as 'Easy' | 'Medium' | 'Hard',
    topic: '',
    count: 1
  })
  const [generating, setGenerating] = useState(false)
  const [generationResult, setGenerationResult] = useState<GenerationResponse | null>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)
  
  // Complete test generation state
  const [completeTestForm, setCompleteTestForm] = useState({
    difficulty: 'Medium' as 'Easy' | 'Medium' | 'Hard',
    include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'] as string[],
    custom_counts: {
      quantitative: 1,
      analogy: 1,
      synonym: 1,
      reading: 1,
      writing: 1
    },
    is_official_format: false,
    provider: 'deepseek' as 'deepseek' | 'gemini' | 'auto'
  })
  const [generatingCompleteTest, setGeneratingCompleteTest] = useState(false)
  const [completeTestResult, setCompleteTestResult] = useState<any>(null)
  const [completeTestError, setCompleteTestError] = useState<string | null>(null)
  
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()

  // Redirect if not authenticated
  React.useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth')
    }
  }, [user, authLoading, router])

  // Fetch official format counts
  React.useEffect(() => {
    const fetchOfficialCounts = async () => {
      try {
        const response = await fetch('/api/specifications/official-format')
        if (response.ok) {
          const data = await response.json()
          setOfficialCounts(data)
        }
      } catch (error) {
        console.error('Failed to fetch official format counts:', error)
      }
    }
    
    fetchOfficialCounts()
  }, [])

  const loadUsers = async () => {
    try {
      setUsersLoading(true)
      setUsersError(null)
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/users', { headers })
      if (response.status === 403) { 
        setUsersError('Access denied. Admin privileges required.')
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
      setUsersError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setUsersLoading(false)
    }
  }

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

      // Update the user in the local state
      setUsers(prevUsers => 
        prevUsers.map(user => 
          user.id === userId ? { ...user, role: newRole } : user
        )
      )
    } catch (err) {
      console.error('Error updating user role:', err)
      alert('Failed to update user role')
    } finally {
      setUpdatingRole(null)
    }
  }

  const handleGenerationSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setGenerating(true)
      setGenerationError(null)
      setGenerationResult(null)
      
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/generate', {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(generationForm)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Generation failed')
      }

      setGenerationResult(data)
    } catch (err) {
      console.error('Error generating content:', err)
      setGenerationError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGenerating(false)
    }
  }

  const handleCompleteTestSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setGeneratingCompleteTest(true)
      setCompleteTestError(null)
      setCompleteTestResult(null)
      
      // Transform the data to match backend CompleteTestRequest model
      const requestData = {
        difficulty: completeTestForm.difficulty,
        include_sections: completeTestForm.include_sections,
        custom_counts: completeTestForm.custom_counts,
        is_official_format: completeTestForm.is_official_format,
        provider: completeTestForm.provider
      }
      
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/generate/complete-test', {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Complete test generation failed')
      }

      setCompleteTestResult(data)
    } catch (err) {
      console.error('Error generating complete test:', err)
      setCompleteTestError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setGeneratingCompleteTest(false)
    }
  }

  const formatLimit = (limit: number) => {
    return limit === -1 ? 'Unlimited' : limit.toString()
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString()
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800'
      case 'premium': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const renderGeneratedContent = (content: any) => {
    if (!content) return null
    
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-md">
        <h4 className="font-medium text-gray-900 mb-2">Generated Content:</h4>
        <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-auto max-h-96">
          {JSON.stringify(content, null, 2)}
        </pre>
      </div>
    )
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="text-lg">Loading authentication...</div>
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null // Will redirect in useEffect
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        </div>

        {/* Navigation Tabs */}
        <div className="mb-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveSection('generate')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'generate'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Single Section
            </button>
            <button
              onClick={() => setActiveSection('complete-test')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'complete-test'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Complete Test
            </button>
            <button
              onClick={() => setActiveSection('users')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Manage Users
            </button>
          </nav>
        </div>

        {/* Generate Content Section */}
        {activeSection === 'generate' && (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                LLM Content Generation
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Generate new questions directly with LLM and add them to the pool (bypasses daily limits).
              </p>
              
              <form onSubmit={handleGenerationSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Question Type</label>
                    <select
                      value={generationForm.question_type}
                      onChange={(e) => setGenerationForm({...generationForm, question_type: e.target.value as any})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="quantitative">Quantitative</option>
                      <option value="analogy">Analogies</option>
                      <option value="synonym">Synonyms</option>
                      <option value="reading">Reading</option>
                      <option value="writing">Writing</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Difficulty</label>
                    <select
                      value={generationForm.difficulty}
                      onChange={(e) => setGenerationForm({...generationForm, difficulty: e.target.value as any})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="Easy">Easy</option>
                      <option value="Medium">Medium</option>
                      <option value="Hard">Hard</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Count</label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={generationForm.count}
                      onChange={(e) => setGenerationForm({...generationForm, count: parseInt(e.target.value)})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Topic (Optional)</label>
                    <input
                      type="text"
                      value={generationForm.topic}
                      onChange={(e) => setGenerationForm({...generationForm, topic: e.target.value})}
                      placeholder="e.g., algebra, geometry"
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
                
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={generating}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {generating ? 'Generating...' : 'Generate Content'}
                  </button>
                </div>
              </form>

              {generationError && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800">
                  Error: {generationError}
                </div>
              )}

              {generationResult && (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
                  <h4 className="font-semibold text-green-800 mb-2">Generation Successful!</h4>
                  <p className="text-sm text-green-700">Session ID: {generationResult.session_id}</p>
                  <p className="text-sm text-green-700">Time: {generationResult.generation_time_ms}ms</p>
                  <p className="text-sm text-green-700">Provider: {generationResult.provider_used}</p>
                  <div className="mt-4">
                    {renderGeneratedContent(generationResult.content)}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Complete Test Generation Section */}
        {activeSection === 'complete-test' && (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                LLM Complete Test Generation
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Generate a complete SSAT test (Quantitative, Verbal, Reading, Writing) with LLM.
              </p>
              
              <form onSubmit={handleCompleteTestSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Difficulty</label>
                    <select
                      value={completeTestForm.difficulty}
                      onChange={(e) => setCompleteTestForm({...completeTestForm, difficulty: e.target.value as any})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="Easy">Easy</option>
                      <option value="Medium">Medium</option>
                      <option value="Hard">Hard</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Test Format</label>
                    <select
                      value={completeTestForm.is_official_format ? 'true' : 'false'}
                      onChange={(e) => setCompleteTestForm({...completeTestForm, is_official_format: e.target.value === 'true'})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="false">Custom</option>
                      <option value="true">Official SSAT Format</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Provider</label>
                    <select
                      value={completeTestForm.provider}
                      onChange={(e) => setCompleteTestForm({...completeTestForm, provider: e.target.value as any})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="auto">Auto</option>
                      <option value="deepseek">DeepSeek</option>
                      <option value="gemini">Gemini</option>
                    </select>
                  </div>
                </div>
                
                {/* Custom Counts - Only show when not official format */}
                {!completeTestForm.is_official_format && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Custom Counts</label>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-500">Quantitative</label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={completeTestForm.custom_counts.quantitative}
                          onChange={(e) => {
                            const value = parseInt(e.target.value) || 1
                            setCompleteTestForm({...completeTestForm, custom_counts: {...completeTestForm.custom_counts, quantitative: value}})
                          }}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500">Analogy</label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={completeTestForm.custom_counts.analogy}
                          onChange={(e) => {
                            const value = parseInt(e.target.value) || 1
                            setCompleteTestForm({...completeTestForm, custom_counts: {...completeTestForm.custom_counts, analogy: value}})
                          }}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500">Synonyms</label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={completeTestForm.custom_counts.synonym}
                          onChange={(e) => {
                            const value = parseInt(e.target.value) || 1
                            setCompleteTestForm({...completeTestForm, custom_counts: {...completeTestForm.custom_counts, synonym: value}})
                          }}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500">Reading</label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={completeTestForm.custom_counts.reading}
                          onChange={(e) => {
                            const value = parseInt(e.target.value) || 1
                            setCompleteTestForm({...completeTestForm, custom_counts: {...completeTestForm.custom_counts, reading: value}})
                          }}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-500">Writing</label>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          value={completeTestForm.custom_counts.writing}
                          onChange={(e) => {
                            const value = parseInt(e.target.value) || 1
                            setCompleteTestForm({...completeTestForm, custom_counts: {...completeTestForm.custom_counts, writing: value}})
                          }}
                          className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                )}
                
                {completeTestForm.is_official_format && officialCounts && (
                  <p className="mt-1 text-xs text-gray-600">
                    Official SSAT Elementary: {officialCounts.quantitative} Quantitative, {officialCounts.analogy} Analogy, {officialCounts.synonym} Synonyms, {officialCounts.reading} Reading passages ({officialCounts.reading * 4} questions), {officialCounts.writing} Writing prompt
                  </p>
                )}
                
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={generatingCompleteTest}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generatingCompleteTest ? 'Generating...' : 'Generate Complete Test'}
                  </button>
                </div>
              </form>
              
              {completeTestError && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-800">Error: {completeTestError}</div>
                </div>
              )}
              
              {completeTestResult && (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
                  <div className="text-green-800 font-medium mb-2">
                    ✅ {completeTestResult.message}
                  </div>
                  <div className="text-sm text-green-700">
                    Session ID: {completeTestResult.session_id}<br/>
                    Sections: {completeTestResult.sections?.join(', ')}<br/>
                    Custom Counts: {JSON.stringify(completeTestResult.custom_counts)}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Users Management Section */}
        {activeSection === 'users' && (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  User Management
                </h3>
                <button
                  onClick={loadUsers}
                  disabled={usersLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {usersLoading ? 'Loading...' : 'Load Users'}
                </button>
              </div>
              
              {usersError && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-800">{usersError}</div>
                </div>
              )}
              
              {users.length > 0 && (
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
                              <div>Synonyms: {formatLimit(userData.limits.synonym)}</div>
                              <div>Reading: {formatLimit(userData.limits.reading_passages)}</div>
                              <div>Writing: {formatLimit(userData.limits.writing)}</div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            <div className="space-y-1">
                              <div>Math: {userData.usage.quantitative_generated}</div>
                              <div>Analogy: {userData.usage.analogy_generated}</div>
                              <div>Synonyms: {userData.usage.synonym_generated}</div>
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
              )}
              
              {users.length === 0 && !usersLoading && !usersError && (
                <div className="text-center py-8 text-gray-500">
                  Click "Load Users" to view user management options
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
} 