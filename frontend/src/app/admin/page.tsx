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

interface StatisticsLoading {
  overview: boolean
  content: boolean
  pool: boolean
}

interface StatisticsError {
  overview: string | null
  content: string | null
  pool: string | null
}

type AdminSection = 'generate' | 'complete-test' | 'users' | 'training-examples' | 'migration' | 'statistics'

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
    count: 1,
    use_custom_examples: false,
    custom_examples: '',
    input_format: 'full' as 'full' | 'simple'
  })
  const [generating, setGenerating] = useState(false)
  const [generationResult, setGenerationResult] = useState<GenerationResponse | null>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)
  
  // Complete test generation state
  const [completeTestForm, setCompleteTestForm] = useState({
    difficulty: 'Medium' as 'Easy' | 'Medium' | 'Hard',
    include_sections: ['quantitative', 'analogy', 'synonym', 'reading', 'writing'] as string[],
    custom_counts: {
      quantitative: 30,
      analogy: 12,
      synonym: 18,
      reading: 7,
      writing: 1
    },
    is_official_format: true,
    provider: 'deepseek' as 'deepseek' | 'gemini' | 'auto'
  })
  const [generatingCompleteTest, setGeneratingCompleteTest] = useState(false)
  const [completeTestResult, setCompleteTestResult] = useState<any>(null)
  const [completeTestError, setCompleteTestError] = useState<string | null>(null)
  
  // Training examples state
  const [trainingExamplesForm, setTrainingExamplesForm] = useState({
    section_type: 'quantitative' as 'quantitative' | 'analogy' | 'synonym' | 'reading' | 'writing',
    examples_text: ''
  })
  const [savingExamples, setSavingExamples] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  
  // Migration state
  const [migrationStats, setMigrationStats] = useState<any>(null)
  const [migrating, setMigrating] = useState(false)
  const [migrationResult, setMigrationResult] = useState<any>(null)
  const [migrationError, setMigrationError] = useState<string | null>(null)
  const [cleaningUp, setCleaningUp] = useState(false)
  const [cleanupResult, setCleanupResult] = useState<any>(null)
  const [cleanupError, setCleanupError] = useState<string | null>(null)
  
  // Statistics state
  const [overviewStats, setOverviewStats] = useState<any>(null)
  const [contentStats, setContentStats] = useState<any>(null)
  const [poolStats, setPoolStats] = useState<any>(null)
  const [statisticsLoading, setStatisticsLoading] = useState<StatisticsLoading>({
    overview: false,
    content: false,
    pool: false
  })
  const [statisticsError, setStatisticsError] = useState<StatisticsError>({
    overview: null,
    content: null,
    pool: null
  })
  
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
        body: JSON.stringify({
          question_type: generationForm.question_type,
          difficulty: generationForm.difficulty,
          topic: generationForm.topic,
          count: (generationForm.question_type === 'synonym' && generationForm.input_format === 'simple') 
            ? generationForm.custom_examples.split(',').filter(word => word.trim()).length 
            : generationForm.count,
          use_custom_examples: generationForm.use_custom_examples || (generationForm.question_type === 'synonym' && generationForm.input_format === 'simple'),
          custom_examples: (generationForm.use_custom_examples || (generationForm.question_type === 'synonym' && generationForm.input_format === 'simple')) ? generationForm.custom_examples : undefined,
          input_format: generationForm.input_format
        })
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
    setGeneratingCompleteTest(true)
    setCompleteTestError(null)
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/generate/complete-test', {
        method: 'POST',
        headers,
        body: JSON.stringify(completeTestForm)
      })
      
      const result = await response.json()
      
      if (response.ok) {
        setCompleteTestResult(result)
      } else {
        setCompleteTestError(result.message || 'Failed to generate complete test')
      }
    } catch (error) {
      setCompleteTestError('Network error. Please try again.')
    } finally {
      setGeneratingCompleteTest(false)
    }
  }

  const handleSaveTrainingExamples = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingExamples(true)
    setSaveError(null)
    setSaveSuccess(null)
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/save-training-examples', {
        method: 'POST',
        headers,
        body: JSON.stringify(trainingExamplesForm)
      })
      
      const result = await response.json()
      
      if (response.ok) {
        const message = `Successfully saved ${result.saved_count} examples for ${trainingExamplesForm.section_type}`
        setSaveSuccess(message)
        setTrainingExamplesForm({...trainingExamplesForm, examples_text: ''})
      } else {
        setSaveError(result.message || 'Failed to save training examples')
      }
    } catch (error) {
      setSaveError('Network error. Please try again.')
    } finally {
      setSavingExamples(false)
    }
  }

  // Migration functions
  const loadMigrationStats = async () => {
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/migration-statistics', { headers })
      
      if (response.ok) {
        const data = await response.json()
        setMigrationStats(data.statistics)
      } else {
        console.error('Failed to load migration statistics')
      }
    } catch (error) {
      console.error('Error loading migration statistics:', error)
    }
  }

  const handleMigration = async () => {
    setMigrating(true)
    setMigrationError(null)
    setMigrationResult(null)
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/migrate-training-to-pool', {
        method: 'POST',
        headers
      })
      
      const result = await response.json()
      
      if (response.ok) {
        setMigrationResult(result)
        // Reload stats after migration
        await loadMigrationStats()
      } else {
        setMigrationError(result.error || 'Migration failed')
      }
    } catch (error) {
      setMigrationError('Network error. Please try again.')
    } finally {
      setMigrating(false)
    }
  }

  const handleCleanup = async () => {
    setCleaningUp(true)
    setCleanupError(null)
    setCleanupResult(null)
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/cleanup-migrated-content', {
        method: 'POST',
        headers
      })
      
      const result = await response.json()
      
      if (response.ok) {
        setCleanupResult(result)
        // Reload stats after cleanup
        await loadMigrationStats()
      } else {
        setCleanupError(result.error || 'Cleanup failed')
      }
    } catch (error) {
      setCleanupError('Network error. Please try again.')
    } finally {
      setCleaningUp(false)
    }
  }

  // Statistics functions
  const loadOverviewStats = async () => {
    setStatisticsLoading(prev => ({ ...prev, overview: true }))
    setStatisticsError(prev => ({ ...prev, overview: null }))
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/statistics/overview', { headers })
      
      if (response.ok) {
        const data = await response.json()
        setOverviewStats(data.statistics)
      } else {
        const errorData = await response.json()
        setStatisticsError(prev => ({ ...prev, overview: errorData.error || 'Failed to load overview statistics' }))
      }
    } catch (error) {
      setStatisticsError(prev => ({ ...prev, overview: 'Network error. Please try again.' }))
    } finally {
      setStatisticsLoading(prev => ({ ...prev, overview: false }))
    }
  }

  const loadContentStats = async () => {
    setStatisticsLoading(prev => ({ ...prev, content: true }))
    setStatisticsError(prev => ({ ...prev, content: null }))
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/statistics/content', { headers })
      
      if (response.ok) {
        const data = await response.json()
        setContentStats(data.statistics)
      } else {
        const errorData = await response.json()
        setStatisticsError(prev => ({ ...prev, content: errorData.error || 'Failed to load content statistics' }))
      }
    } catch (error) {
      setStatisticsError(prev => ({ ...prev, content: 'Network error. Please try again.' }))
    } finally {
      setStatisticsLoading(prev => ({ ...prev, content: false }))
    }
  }

  const loadPoolStats = async () => {
    setStatisticsLoading(prev => ({ ...prev, pool: true }))
    setStatisticsError(prev => ({ ...prev, pool: null }))
    
    try {
      const headers = await getAuthHeaders()
      const response = await fetch('/api/admin/statistics/pool', { headers })
      
      if (response.ok) {
        const data = await response.json()
        setPoolStats(data.statistics)
      } else {
        const errorData = await response.json()
        setStatisticsError(prev => ({ ...prev, pool: errorData.error || 'Failed to load pool statistics' }))
      }
    } catch (error) {
      setStatisticsError(prev => ({ ...prev, pool: 'Network error. Please try again.' }))
    } finally {
      setStatisticsLoading(prev => ({ ...prev, pool: false }))
    }
  }

  // Load migration stats when migration section is active
  React.useEffect(() => {
    if (activeSection === 'migration') {
      loadMigrationStats()
    }
  }, [activeSection])

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
            <button
              onClick={() => setActiveSection('training-examples')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'training-examples'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Save AI Training Examples
            </button>
            <button
              onClick={() => setActiveSection('migration')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'migration'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Migrate Training Examples to Pool
            </button>
            <button
              onClick={() => setActiveSection('statistics')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeSection === 'statistics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📊 Statistics
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
                      onChange={(e) => setGenerationForm({
                        ...generationForm, 
                        question_type: e.target.value as any,
                        // Reset custom examples and topic when switching sections
                        use_custom_examples: false,
                        custom_examples: '',
                        topic: ''
                      })}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="quantitative">Quantitative</option>
                      <option value="analogy">Analogies</option>
                      <option value="synonym">Synonyms</option>
                      <option value="reading">Reading</option>
                      <option value="writing">Writing</option>
                    </select>
                  </div>
                  
                  {generationForm.question_type === 'synonym' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Input Format</label>
                      <select
                        value={generationForm.input_format}
                        onChange={(e) => {
                          const newFormat = e.target.value as 'full' | 'simple';
                          setGenerationForm({
                            ...generationForm, 
                            input_format: newFormat,
                            // Auto-enable custom examples for simple word list
                            use_custom_examples: newFormat === 'simple' ? true : generationForm.use_custom_examples
                          });
                        }}
                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="full">Full Question Format</option>
                        <option value="simple">Simple Word List</option>
                      </select>
                    </div>
                  )}
                  
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
                  
                  {generationForm.question_type === 'synonym' && generationForm.input_format === 'simple' ? (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Word Count</label>
                      <div className="mt-1 p-2 bg-gray-50 border border-gray-300 rounded-md text-sm text-gray-600">
                        {generationForm.custom_examples 
                          ? `${generationForm.custom_examples.split(',').filter(word => word.trim()).length} words detected`
                          : 'Enter words to see count'
                        }
                      </div>
                    </div>
                  ) : (
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
                  )}
                  
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
                
                {/* Quantitative Subsections Display */}
                {generationForm.question_type === 'quantitative' && (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <h5 className="text-sm font-medium text-blue-900 mb-2">Available Quantitative Subsections</h5>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                      <div className="text-xs font-medium text-blue-800 mb-1 col-span-full">Number Operations (40%):</div>
                      <div className="text-xs text-blue-700">Number Sense</div>
                      <div className="text-xs text-blue-700">Arithmetic</div>
                      <div className="text-xs text-blue-700">Fractions</div>
                      <div className="text-xs text-blue-700">Decimals</div>
                      <div className="text-xs text-blue-700">Percentages</div>
                      
                      <div className="text-xs font-medium text-blue-800 mb-1 col-span-full">Algebra Functions (20%):</div>
                      <div className="text-xs text-blue-700">Patterns</div>
                      <div className="text-xs text-blue-700">Sequences</div>
                      <div className="text-xs text-blue-700">Algebra</div>
                      <div className="text-xs text-blue-700">Variables</div>
                      
                      <div className="text-xs font-medium text-blue-800 mb-1 col-span-full">Geometry Spatial (25%):</div>
                      <div className="text-xs text-blue-700">Area</div>
                      <div className="text-xs text-blue-700">Perimeter</div>
                      <div className="text-xs text-blue-700">Shapes</div>
                      <div className="text-xs text-blue-700">Spatial</div>
                      
                      <div className="text-xs font-medium text-blue-800 mb-1 col-span-full">Measurement (10%):</div>
                      <div className="text-xs text-blue-700">Measurement</div>
                      <div className="text-xs text-blue-700">Time</div>
                      <div className="text-xs text-blue-700">Money</div>
                      
                      <div className="text-xs font-medium text-blue-800 mb-1 col-span-full">Probability Data (5%):</div>
                      <div className="text-xs text-blue-700">Probability</div>
                      <div className="text-xs text-blue-700">Data</div>
                      <div className="text-xs text-blue-700">Graphs</div>
                    </div>
                    <p className="text-xs text-blue-600 mt-2">
                      <strong>Tip:</strong> Use these subsection names as topics for more targeted question generation.
                    </p>
                  </div>
                )}
                
                {/* Custom Training Examples Section */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-md font-medium text-gray-900">Custom Training Examples</h4>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="use_custom_examples"
                        checked={generationForm.use_custom_examples}
                        onChange={(e) => setGenerationForm({...generationForm, use_custom_examples: e.target.checked})}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor="use_custom_examples" className="ml-2 text-sm text-gray-700">
                        Use custom examples instead of database examples
                      </label>
                    </div>
                  </div>
                  
                  {(generationForm.use_custom_examples || (generationForm.question_type === 'synonym' && generationForm.input_format === 'simple')) && (
                    <div className="space-y-4">
                      {generationForm.question_type === 'synonym' && generationForm.input_format === 'simple' && (
                        <div className="bg-green-50 border border-green-200 rounded-md p-3">
                          <p className="text-sm text-green-800">
                            <strong>Simple Word List Mode:</strong> Enter words separated by commas. The system will automatically generate synonym questions for all words you enter. The word count is calculated automatically.
                          </p>
                        </div>
                      )}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {generationForm.question_type === 'synonym' && generationForm.input_format === 'simple' 
                            ? 'Word List (Enter words separated by commas)' 
                            : 'Training Examples (Paste your examples below)'}
                        </label>
                        <textarea
                          value={generationForm.custom_examples}
                          onChange={(e) => setGenerationForm({...generationForm, custom_examples: e.target.value})}
                          placeholder={
                            generationForm.question_type === 'synonym' && generationForm.input_format === 'simple'
                              ? "Enter words separated by commas (e.g., happy, sad, big, small)..."
                              : "Paste your training examples here..."
                          }
                          rows={8}
                          className="block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      
                      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                        <h5 className="text-sm font-medium text-blue-900 mb-2">Format Instructions</h5>
                        <div className="text-sm text-blue-800 space-y-2">
                          {generationForm.question_type === 'quantitative' && (
                            <div>
                              <p className="font-medium">Quantitative Questions Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`Question: What is 1/4 + 1/2?
Choices: A) 1/6; B) 2/6; C) 3/4; D) 3/6
Correct Answer: C
Explanation: To add fractions, find a common denominator. 1/4 + 1/2 = 1/4 + 2/4 = 3/4
Difficulty: Easy
Subsection: Fractions

Question: If x + 5 = 12, what is the value of x?
Choices: A) 5; B) 6; C) 7; D) 8
Correct Answer: C
Explanation: Subtract 5 from both sides: x = 12 - 5 = 7
Difficulty: Easy
Subsection: Algebra

Question: What is the area of a rectangle with length 8 and width 5?
Choices: A) 13; B) 26; C) 40; D) 45
Correct Answer: C
Explanation: Area of rectangle = length × width = 8 × 5 = 40
Difficulty: Easy
Subsection: Geometry`}
                              </pre>
                            </div>
                          )}
                          
                          {generationForm.question_type === 'analogy' && (
                            <div>
                              <p className="font-medium">Analogy Questions Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`Question: Dog is to puppy as cat is to:
Choices: A) kitten; B) mouse; C) bird; D) fish
Correct Answer: A
Explanation: A puppy is a young dog, just as a kitten is a young cat.
Difficulty: Easy
Subsection: Analogies

Question: Author is to book as composer is to:
Choices: A) painting; B) sculpture; C) symphony; D) poem
Correct Answer: C
Explanation: An author creates books, just as a composer creates symphonies (musical compositions).
Difficulty: Medium
Subsection: Analogies

Question: Ephemeral is to permanent as turbulent is to:
Choices: A) chaotic; B) peaceful; C) stormy; D) violent
Correct Answer: B
Explanation: Ephemeral (short-lasting) is opposite to permanent, just as turbulent (chaotic) is opposite to peaceful.
Difficulty: Hard
Subsection: Analogies`}
                              </pre>
                            </div>
                          )}
                          
                          {generationForm.question_type === 'synonym' && generationForm.input_format === 'simple' && (
                            <div>
                              <p className="font-medium">Simple Word List Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`happy, sad, big, small, fast, slow, hot, cold, loud, quiet`}
                              </pre>
                                                    <p className="text-xs text-blue-700 mt-2">
                        <strong>How it works:</strong> Enter words separated by commas. The system will automatically generate synonym questions for all words you enter. The word count is calculated automatically.
                      </p>
                            </div>
                          )}
                          {generationForm.question_type === 'synonym' && generationForm.input_format === 'full' && (
                            <div>
                              <p className="font-medium">Synonym Questions Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`Question: Choose the word that is most similar in meaning to "happy"
Choices: A) sad; B) joyful; C) angry; D) tired
Correct Answer: B
Explanation: Joyful means feeling great pleasure and happiness, making it the best synonym for happy.
Difficulty: Easy
Subsection: Synonyms

Question: Choose the word that is most similar in meaning to "meticulous"
Choices: A) careless; B) detailed; C) quick; D) loud
Correct Answer: B
Explanation: Meticulous means showing great attention to detail; very careful and precise.
Difficulty: Medium
Subsection: Synonyms

Question: Choose the word that is most similar in meaning to "ubiquitous"
Choices: A) rare; B) everywhere; C) hidden; D) expensive
Correct Answer: B
Explanation: Ubiquitous means present, appearing, or found everywhere.
Difficulty: Hard
Subsection: Synonyms`}
                              </pre>
                            </div>
                          )}
                          
                          {generationForm.question_type === 'reading' && (
                            <div>
                              <p className="font-medium">Reading Questions Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`PASSAGE:
The butterfly is one of nature's most beautiful creatures. With colorful wings 
that seem to dance in the air, butterflies bring joy to gardens everywhere. 
They start their lives as caterpillars, eating leaves and growing bigger each 
day. Then they form a chrysalis and undergo an amazing transformation called 
metamorphosis.

PASSAGE TYPE: Science Fiction
DIFFICULTY: Medium

QUESTION: According to the passage, what do caterpillars do before becoming butterflies?
CHOICES: A) They fly around gardens; B) They form a chrysalis; C) They dance in the air; D) They bring joy to people
CORRECT ANSWER: B
EXPLANATION: The passage states that caterpillars "form a chrysalis and undergo an amazing transformation called metamorphosis."

QUESTION: What is the main idea of this passage?
CHOICES: A) Butterflies are beautiful; B) The life cycle of butterflies; C) Gardens need butterflies; D) Metamorphosis is amazing
CORRECT ANSWER: B
EXPLANATION: The passage describes the complete life cycle from caterpillar to butterfly, making this the main idea.

QUESTION: What happens during metamorphosis?
CHOICES: A) Caterpillars eat more leaves; B) Wings develop inside the chrysalis; C) Butterflies lay eggs; D) Caterpillars grow bigger
CORRECT ANSWER: B
EXPLANATION: The passage mentions that caterpillars "undergo an amazing transformation called metamorphosis" inside the chrysalis.

QUESTION: Why are butterflies important to gardens?
CHOICES: A) They eat harmful insects; B) They bring joy to people; C) They help plants grow; D) They provide food for birds
CORRECT ANSWER: B
EXPLANATION: The passage states that butterflies "bring joy to gardens everywhere."`}
                              </pre>
                            </div>
                          )}
                          
                          {generationForm.question_type === 'writing' && (
                            <div>
                              <p className="font-medium">Writing Prompts Format:</p>
                              <pre className="text-xs bg-blue-100 p-2 rounded mt-1">
{`Prompt: Look at this picture of children building a treehouse. Write a story about their adventure.
Visual Description: Children working together with wood and tools to build a treehouse
Grade Level: 3-4
Prompt Type: picture_story
Subsection: Collaborative Problem-Solving Narratives
Tags: teamwork-themes, problem-solving-process, character-interaction

Prompt: You find a magic key that can open any door. Write a story about where you go and what you discover.
Visual Description: An ornate, glowing key lying on a wooden table
Grade Level: 3-4
Prompt Type: creative_story
Subsection: Imaginative Adventure Stories
Tags: imaginative-thinking, creative-problem-solving, world-building`}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
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
                    <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                      Official SSAT Format
                    </div>
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
                
                {/* Official Counts Display */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Official SSAT Counts</label>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500">Quantitative</label>
                      <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                        30
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500">Analogy</label>
                      <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                        12
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500">Synonyms</label>
                      <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                        18
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500">Reading</label>
                      <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                        7
                      </div>
                    </div>
                                          <div>
                        <label className="block text-xs font-medium text-gray-500">Writing</label>
                        <div className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-100 text-gray-600">
                          1
                        </div>
                      </div>
                    </div>
                  </div>
                
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
                    <>Official Counts: {JSON.stringify(completeTestResult.custom_counts)}</>
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

        {/* AI Training Examples Section */}
        {activeSection === 'training-examples' && (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                AI Training Examples
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Save training examples to the database for use in LLM generation. Examples will be automatically used by the generator.
              </p>
              
              <form onSubmit={handleSaveTrainingExamples} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Section Type</label>
                    <select
                      value={trainingExamplesForm.section_type}
                      onChange={(e) => setTrainingExamplesForm({...trainingExamplesForm, section_type: e.target.value as any})}
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="quantitative">Quantitative</option>
                      <option value="analogy">Analogies</option>
                      <option value="synonym">Synonyms</option>
                      <option value="reading">Reading</option>
                      <option value="writing">Writing</option>
                    </select>
                  </div>

                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Training Examples
                  </label>
                  <textarea
                    value={trainingExamplesForm.examples_text}
                    onChange={(e) => setTrainingExamplesForm({...trainingExamplesForm, examples_text: e.target.value})}
                    placeholder="Paste your training examples here..."
                    rows={12}
                    className="block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Format: For Quantitative/Analogies/Synonyms, use "Question:", "Choices:", "Correct Answer:", "Explanation:". 
                    For Reading, use "PASSAGE:", "PASSAGE TYPE:", "DIFFICULTY:", then "QUESTION:", "CHOICES:", "CORRECT ANSWER:", "EXPLANATION:" for each question. For Writing, use "Prompt:" format.
                    <strong> All questions must have exactly 4 choices (A, B, C, D). Use semicolons (;) to separate choices when they contain commas.</strong>
                  </p>
                  <div className="mt-2 text-sm text-gray-600">
                    <p className="font-medium mb-2">Format Instructions:</p>
                    {trainingExamplesForm.section_type === 'quantitative' && (
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="font-medium text-blue-900 mb-2">Quantitative Format:</p>
                        <pre className="text-xs text-blue-800 whitespace-pre-wrap">
{`Question: What is 1/4 + 1/2?
Choices: A) 1/6, B) 2/6, C) 3/4, D) 3/6
Correct Answer: C
Explanation: To add fractions, find a common denominator. 1/4 + 1/2 = 1/4 + 2/4 = 3/4
Difficulty: Easy
Subsection: Fraction Operations
Tags: fraction-concepts, computational-fluency

Question: If 3(x - 2) = 2(x + 1) + 5, what is the value of x?
Choices: A) 11, B) 12, C) 13, D) 14
Correct Answer: C
Explanation: Expand: 3x - 6 = 2x + 2 + 5, so 3x - 6 = 2x + 7. Solving: x = 13
Difficulty: Hard
Subsection: Complex Algebraic Equations
Tags: algebraic-thinking, multi-step-solution`}
                        </pre>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Database:</strong> Section="Quantitative", Subsection=your custom subsection, Tags=your custom tags
                        </p>
                      </div>
                    )}
                    {trainingExamplesForm.section_type === 'analogy' && (
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="font-medium text-blue-900 mb-2">Analogies Format:</p>
                        <pre className="text-xs text-blue-800 whitespace-pre-wrap">
{`Question: Book is to reading as fork is to:
Choices: A) eating, B) cooking, C) kitchen, D) food
Correct Answer: A
Explanation: A book is used for reading, just as a fork is used for eating.
Difficulty: Easy
Tags: function-relationships, tool-purpose

Question: Doctor is to hospital as teacher is to:
Choices: A) classroom, B) students, C) education, D) school
Correct Answer: D
Explanation: A doctor works in a hospital, just as a teacher works in a school.
Difficulty: Medium
Tags: professional-settings, workplace-relationships`}
                        </pre>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Database:</strong> Section="Verbal", Subsection="Analogies", Tags=your custom tags
                        </p>
                      </div>
                    )}
                    {trainingExamplesForm.section_type === 'synonym' && (
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="font-medium text-blue-900 mb-2">Synonyms Format:</p>
                        <pre className="text-xs text-blue-800 whitespace-pre-wrap">
{`Question: Which word means the same as "happy"?
Choices: A) sad, B) joyful, C) angry, D) tired
Correct Answer: B
Explanation: "Joyful" is a synonym for "happy" - both mean feeling pleasure or contentment.
Difficulty: Easy
Tags: basic-synonyms, emotion-words

Question: What is a synonym for "enormous"?
Choices: A) tiny, B) huge, C) small, D) medium
Correct Answer: B
Explanation: "Huge" is a synonym for "enormous" - both mean very large in size.
Difficulty: Medium
Tags: size-descriptors, vocabulary-building`}
                        </pre>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Database:</strong> Section="Verbal", Subsection="Synonyms", Tags=your custom tags
                        </p>
                      </div>
                    )}
                    {trainingExamplesForm.section_type === 'reading' && (
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="font-medium text-blue-900 mb-2">Reading Format (1 passage + 4 questions):</p>
                        <pre className="text-xs text-blue-800 whitespace-pre-wrap">
{`PASSAGE:
The ancient city of Rome was founded in 753 BCE and grew to become one of 
the most powerful empires in history. The Romans were known for their 
advanced engineering, including the construction of roads, aqueducts, and 
impressive buildings like the Colosseum. They also developed a sophisticated 
legal system that influenced modern law. The Roman Empire reached its peak 
around 117 CE, covering most of Europe, North Africa, and parts of Asia.

PASSAGE TYPE: History Non-Fiction
DIFFICULTY: Medium

QUESTION: When was Rome founded?
CHOICES: A) 753 BCE; B) 753 CE; C) 117 BCE; D) 117 CE
CORRECT ANSWER: A
EXPLANATION: The passage states that Rome was founded in 753 BCE.

QUESTION: What was one of the Romans' most notable achievements?
CHOICES: A) Writing poetry; B) Advanced engineering; C) Painting; D) Music
CORRECT ANSWER: B
EXPLANATION: The passage mentions that Romans were known for their advanced engineering.

QUESTION: What type of building is mentioned in the passage?
CHOICES: A) Library; B) Temple; C) Colosseum; D) Bridge
CORRECT ANSWER: C
EXPLANATION: The passage specifically mentions the Colosseum as an example of Roman engineering.

QUESTION: Around what year did the Roman Empire reach its peak?
CHOICES: A) 753 BCE; B) 753 CE; C) 117 BCE; D) 117 CE
CORRECT ANSWER: D
EXPLANATION: The passage states the empire reached its peak around 117 CE.

QUESTION: What was the purpose of the Roman legal system?
CHOICES: A) To collect taxes; B) To influence modern law; C) To build roads; D) To train soldiers
CORRECT ANSWER: B
EXPLANATION: The passage mentions that Romans "developed a sophisticated legal system that influenced modern law."`}
                        </pre>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Database:</strong> Saved to reading_passages + reading_questions tables, all questions inherit passage difficulty
                        </p>
                      </div>
                    )}
                    {trainingExamplesForm.section_type === 'writing' && (
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="font-medium text-blue-900 mb-2">Writing Format (Picture-Based Prompts):</p>
                        <pre className="text-xs text-blue-800 whitespace-pre-wrap">
{`Prompt: Look at this picture of children building a treehouse. Write a story about their adventure.
Visual Description: Children working together with wood and tools to build a treehouse in a backyard
Tags: character-development, visual-inspiration, adventure-elements

Prompt: You find a magic key that can open any door. Write a story about where you go and what you discover.
Visual Description: An ornate, glowing key lying on a wooden table with mysterious symbols
Tags: imaginative-thinking, creative-problem-solving, discovery-learning

Prompt: A friendly robot appears in your backyard. Write a story about what happens next.
Visual Description: Small, colorful robot with friendly LED eyes standing in a garden
Tags: character-development, visual-inspiration, friendship-themes`}
                        </pre>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Visual Description Guidelines:</strong>
                          • Describe the picture that would accompany the prompt
                          • Include key visual elements: people, objects, setting, colors, actions
                          • Be specific but concise (1-2 sentences)
                          • Focus on elements that inspire storytelling
                          • Use age-appropriate language for grades 3-4
                        </p>
                        <p className="text-xs text-blue-700 mt-2">
                          <strong>Database:</strong> Saved to writing_prompts table with visual_description field
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {saveSuccess && (
                  <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
                    <div className="text-green-800">{saveSuccess}</div>
                  </div>
                )}

                {saveError && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <div className="text-red-800">{saveError}</div>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={savingExamples || !trainingExamplesForm.examples_text.trim()}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {savingExamples ? 'Saving...' : 'Save Training Examples'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Migration Section */}
        {activeSection === 'migration' && (
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Training Examples Migration
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Smart migration that migrates only new training examples to the user-facing pool (skips already migrated items).
              </p>
              
              {/* Migration Statistics */}
              {migrationStats && (
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-3">Current Statistics</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">Training Content</h5>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>Questions: {migrationStats.training_content?.questions || 0}</div>
                        <div>Passages: {migrationStats.training_content?.passages || 0}</div>
                        <div>Reading Questions: {migrationStats.training_content?.reading_questions || 0}</div>
                        <div>Writing Prompts: {migrationStats.training_content?.writing_prompts || 0}</div>
                      </div>
                    </div>
                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">User Pool Content</h5>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>Questions: {migrationStats.pool_content?.questions || 0}</div>
                        <div>Passages: {migrationStats.pool_content?.passages || 0}</div>
                        <div>Reading Questions: {migrationStats.pool_content?.reading_questions || 0}</div>
                        <div>Writing Prompts: {migrationStats.pool_content?.writing_prompts || 0}</div>
                      </div>
                    </div>
                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">Migration Status</h5>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>Questions Migrated: {migrationStats.migrated_content?.questions || 0}</div>
                        <div>Passages Migrated: {migrationStats.migrated_content?.passages || 0}</div>
                        <div>Reading Questions Migrated: {migrationStats.migrated_content?.reading_questions || 0}</div>
                        <div>Writing Prompts Migrated: {migrationStats.migrated_content?.writing_prompts || 0}</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-sm text-gray-600">
                      <strong>Smart Migration:</strong> Only migrates new content (skips already migrated items)
                    </div>
                  </div>
                </div>
              )}
              
              {/* Migration Actions */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                  <div>
                    <h4 className="font-medium text-blue-900">Smart Migration</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      Migrate only new or changed training examples to the user pool
                    </p>
                  </div>
                  <button
                    onClick={handleMigration}
                    disabled={migrating}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {migrating ? 'Migrating...' : 'Start Migration'}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                  <div>
                    <h4 className="font-medium text-red-900">Cleanup Migrated Content</h4>
                    <p className="text-sm text-red-700 mt-1">
                      Remove migrated content from the user pool (if needed)
                    </p>
                  </div>
                  <button
                    onClick={handleCleanup}
                    disabled={cleaningUp}
                    className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {cleaningUp ? 'Cleaning...' : 'Cleanup'}
                  </button>
                </div>
              </div>
              
              {/* Migration Results */}
              {migrationResult && (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
                  <div className="text-green-800 font-medium mb-2">
                    ✅ {migrationResult.message}
                  </div>
                  <div className="text-sm text-green-700">
                    <div>Questions Migrated: {migrationResult.migration_results?.questions_migrated || 0}</div>
                    <div>Passages Migrated: {migrationResult.migration_results?.passages_migrated || 0}</div>
                    <div>Reading Questions Migrated: {migrationResult.migration_results?.reading_questions_migrated || 0}</div>
                    <div>Writing Prompts Migrated: {migrationResult.migration_results?.writing_prompts_migrated || 0}</div>
                    <div>Total Skipped: {migrationResult.migration_results?.total_skipped || 0}</div>
                    <div>Total Errors: {migrationResult.migration_results?.total_errors || 0}</div>
                  </div>
                </div>
              )}
              
              {migrationError && (
                <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-800">Error: {migrationError}</div>
                </div>
              )}
              
              {/* Cleanup Results */}
              {cleanupResult && (
                <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <div className="text-yellow-800 font-medium mb-2">
                    ✅ {cleanupResult.message}
                  </div>
                  <div className="text-sm text-yellow-700">
                    <div>Questions Removed: {cleanupResult.cleanup_results?.questions_removed || 0}</div>
                    <div>Passages Removed: {cleanupResult.cleanup_results?.passages_removed || 0}</div>
                    <div>Reading Questions Removed: {cleanupResult.cleanup_results?.reading_questions_removed || 0}</div>
                    <div>Writing Prompts Removed: {cleanupResult.cleanup_results?.writing_prompts_removed || 0}</div>
                  </div>
                </div>
              )}
              
              {cleanupError && (
                <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-800">Error: {cleanupError}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Statistics Section */}
        {activeSection === 'statistics' && (
          <div className="space-y-6">
            {/* Platform Overview Statistics */}
            <div className="bg-white shadow sm:rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      🏢 Platform Overview
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      High-level metrics showing total users, content volume, and generation performance
                    </p>
                  </div>
                  <button
                    onClick={loadOverviewStats}
                    disabled={statisticsLoading.overview}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {statisticsLoading.overview ? 'Loading...' : 'Load Overview Stats'}
                  </button>
                </div>
                
                {statisticsError.overview && (
                  <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="text-red-800">Error: {statisticsError.overview}</div>
                  </div>
                )}
                
                {overviewStats && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">Users</h4>
                      <div className="text-sm space-y-1">
                        <div className="text-2xl font-bold text-blue-600">{overviewStats.users.total_users}</div>
                      </div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <h4 className="font-medium text-green-900 mb-2">Content</h4>
                      <div className="text-sm space-y-1">
                        <div>Training: {overviewStats.content.total_training_content}</div>
                        <div>AI Generated: {overviewStats.content.total_ai_generated_content}</div>
                      </div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <h4 className="font-medium text-purple-900 mb-2">Generation Health</h4>
                      <div className="text-sm space-y-1">
                        <div>Sessions: {overviewStats.generation.total_generation_sessions}</div>
                        <div>Success (7d): {overviewStats.generation.successful_generations_last_7_days}</div>
                        <div>Failed (7d): {overviewStats.generation.failed_generations_last_7_days}</div>
                        <div>Success Rate: {overviewStats.generation.success_rate_percentage}%</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Content Breakdown Statistics */}
            <div className="bg-white shadow sm:rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      📚 Content Analysis
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Breakdown of training examples vs AI-generated content by question type
                    </p>
                  </div>
                  <button
                    onClick={loadContentStats}
                    disabled={statisticsLoading.content}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {statisticsLoading.content ? 'Loading...' : 'Load Content Stats'}
                  </button>
                </div>
                
                {statisticsError.content && (
                  <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="text-red-800">Error: {statisticsError.content}</div>
                  </div>
                )}
                
                {contentStats && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-indigo-50 p-4 rounded-lg">
                      <h4 className="font-medium text-indigo-900 mb-2">Training Content</h4>
                      <div className="space-y-1 text-sm">
                        <div>Quantitative: {contentStats.training_content.quantitative}</div>
                        <div>Analogies: {contentStats.training_content.analogies}</div>
                        <div>Synonyms: {contentStats.training_content.synonyms}</div>
                        <div>Reading Passages: {contentStats.training_content.reading_passages}</div>
                        <div>Reading Questions: {contentStats.training_content.reading_questions}</div>
                        <div>Writing Prompts: {contentStats.training_content.writing_prompts}</div>
                      </div>
                    </div>
                    <div className="bg-emerald-50 p-4 rounded-lg">
                      <h4 className="font-medium text-emerald-900 mb-2">AI Generated Content (Pool)</h4>
                      <div className="space-y-1 text-sm">
                        <div>Quantitative: {contentStats.ai_generated_content.quantitative}</div>
                        <div>Analogies: {contentStats.ai_generated_content.analogies}</div>
                        <div>Synonyms: {contentStats.ai_generated_content.synonyms}</div>
                        <div>Reading Passages: {contentStats.ai_generated_content.reading_passages}</div>
                        <div>Reading Questions: {contentStats.ai_generated_content.reading_questions}</div>
                        <div>Writing Prompts: {contentStats.ai_generated_content.writing_prompts}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Pool Utilization Statistics */}
            <div className="bg-white shadow sm:rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      🎯 Pool Utilization
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      AI-generated content usage across all sections (Quantitative, Analogies, Synonyms, Reading, Writing) with remaining counts
                    </p>
                  </div>
                  <button
                    onClick={loadPoolStats}
                    disabled={statisticsLoading.pool}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {statisticsLoading.pool ? 'Loading...' : 'Load Pool Stats'}
                  </button>
                </div>
                
                {statisticsError.pool && (
                  <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="text-red-800">Error: {statisticsError.pool}</div>
                  </div>
                )}
                
                {poolStats && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className="bg-blue-50 p-3 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">Quantitative</h4>
                      <div className="text-sm space-y-1">
                        <div>Used: {poolStats.quantitative.used}</div>
                        <div>Remaining: {poolStats.quantitative.remaining}</div>
                      </div>
                    </div>
                    <div className="bg-green-50 p-3 rounded-lg">
                      <h4 className="font-medium text-green-900 mb-2">Analogies</h4>
                      <div className="text-sm space-y-1">
                        <div>Used: {poolStats.analogy.used}</div>
                        <div>Remaining: {poolStats.analogy.remaining}</div>
                      </div>
                    </div>
                    <div className="bg-purple-50 p-3 rounded-lg">
                      <h4 className="font-medium text-purple-900 mb-2">Synonyms</h4>
                      <div className="text-sm space-y-1">
                        <div>Used: {poolStats.synonym.used}</div>
                        <div>Remaining: {poolStats.synonym.remaining}</div>
                      </div>
                    </div>
                    <div className="bg-orange-50 p-3 rounded-lg">
                      <h4 className="font-medium text-orange-900 mb-2">Reading</h4>
                      <div className="text-sm space-y-1">
                        <div>Used: {poolStats.reading.used}</div>
                        <div>Remaining: {poolStats.reading.remaining}</div>
                      </div>
                    </div>
                    <div className="bg-teal-50 p-3 rounded-lg">
                      <h4 className="font-medium text-teal-900 mb-2">Writing</h4>
                      <div className="text-sm space-y-1">
                        <div>Used: {poolStats.writing.used}</div>
                        <div>Remaining: {poolStats.writing.remaining}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
} 