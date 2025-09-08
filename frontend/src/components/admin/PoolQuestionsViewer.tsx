'use client'

import React, { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, BookOpen, Calculator, FileText, PenTool, Brain, Copy, Edit, Trash2 } from 'lucide-react'
import { getAuthHeaders } from '@/utils/auth'

interface PoolQuestion {
  id: string
  question?: string
  choices?: string[]
  answer?: number
  explanation?: string
  difficulty?: string
  tags?: string[]
  prompt?: string
  passage?: string
  questions?: PoolQuestion[]
  generation_session_id?: string
  training_examples_used?: string[]
  created_at?: string
}

interface PoolQuestionsData {
  success: boolean
  summary: {
    quantitative: number
    analogy: number
    synonym: number
    reading_passages: number
    reading_questions: number
    writing: number
  }
  pool_questions: {
    quantitative: PoolQuestion[]
    analogy: PoolQuestion[]
    synonym: PoolQuestion[]
    reading: PoolQuestion[]
    writing: PoolQuestion[]
  }
}

interface PoolQuestionsViewerProps {
  showChinese?: boolean
}

export function PoolQuestionsViewer({ showChinese = false }: PoolQuestionsViewerProps) {
  const [data, setData] = useState<PoolQuestionsData | null>(null)
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [loadedSections, setLoadedSections] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [editingQuestion, setEditingQuestion] = useState<PoolQuestion | null>(null)
  const [editForm, setEditForm] = useState<Partial<PoolQuestion>>({})
  const [sectionDifficultyFilters, setSectionDifficultyFilters] = useState<Record<string, string>>({
    quantitative: '',
    analogy: '',
    synonym: '',
    reading: '',
    writing: ''
  })
  const [unfilteredData, setUnfilteredData] = useState<PoolQuestionsData | null>(null) // Store unfiltered data

  // Effect to filter data when any section difficulty filter changes
  useEffect(() => {
    if (unfilteredData) {
      const filteredData = {
        ...unfilteredData,
        pool_questions: {
          quantitative: sectionDifficultyFilters.quantitative 
            ? unfilteredData.pool_questions.quantitative.filter(item => item.difficulty === sectionDifficultyFilters.quantitative)
            : unfilteredData.pool_questions.quantitative,
          analogy: sectionDifficultyFilters.analogy 
            ? unfilteredData.pool_questions.analogy.filter(item => item.difficulty === sectionDifficultyFilters.analogy)
            : unfilteredData.pool_questions.analogy,
          synonym: sectionDifficultyFilters.synonym 
            ? unfilteredData.pool_questions.synonym.filter(item => item.difficulty === sectionDifficultyFilters.synonym)
            : unfilteredData.pool_questions.synonym,
          reading: sectionDifficultyFilters.reading 
            ? unfilteredData.pool_questions.reading.map(passage => ({
                ...passage,
                questions: passage.questions?.filter((q: PoolQuestion) => q.difficulty === sectionDifficultyFilters.reading) || []
              })).filter(passage => passage.questions && passage.questions.length > 0)
            : unfilteredData.pool_questions.reading,
          writing: unfilteredData.pool_questions.writing // Writing prompts don't have difficulty
        }
      }
      
      // Update summary counts
      filteredData.summary = {
        quantitative: filteredData.pool_questions.quantitative.length,
        analogy: filteredData.pool_questions.analogy.length,
        synonym: filteredData.pool_questions.synonym.length,
        reading_passages: filteredData.pool_questions.reading.length,
        reading_questions: filteredData.pool_questions.reading.reduce((sum, passage) => sum + (passage.questions?.length || 0), 0),
        writing: filteredData.pool_questions.writing.length
      }
      
      setData(filteredData)
    }
  }, [unfilteredData, sectionDifficultyFilters])

  const copyToClipboard = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000) // Clear after 2 seconds
    } catch (err) {
      console.error('Failed to copy ID:', err)
    }
  }

  const renderIdDisplay = (id: string) => {
    const isCopied = copiedId === id
    return (
      <div className="flex items-center gap-1">
        <span className="text-xs font-mono bg-gray-200 text-gray-700 px-2 py-1 rounded">
          ID: {id}
        </span>
        <button
          onClick={(e) => {
            e.preventDefault()
            copyToClipboard(id)
          }}
          className="text-gray-500 hover:text-gray-700 transition-colors"
          title="Copy ID to clipboard"
        >
          <Copy className="w-3 h-3" />
        </button>
        {isCopied && (
          <span className="text-xs text-green-600 font-medium">Copied!</span>
        )}
      </div>
    )
  }

  const deletePoolQuestion = async (id: string, section: string) => {
    if (!confirm(`Are you sure you want to delete this pool question?\n\nID: ${id}\n\nThis action cannot be undone.`)) {
      return
    }

    try {
      setDeletingId(id)
      const headers = await getAuthHeaders()
      
      // Determine the table based on section
      let tableName = ''
      if (section === 'reading') {
        tableName = 'ai_generated_reading_passages' // For reading, we delete the passage which cascades to questions
      } else if (section === 'writing') {
        tableName = 'ai_generated_writing_prompts'
      } else {
        tableName = 'ai_generated_questions'
      }

      const response = await fetch(`/api/admin/pool-questions/${id}`, {
        method: 'DELETE',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ table: tableName })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to delete pool question')
      }

      // Remove from local state
      setData(prev => {
        if (!prev) return prev
        
        const updatedData = { ...prev }
        if (section === 'reading') {
          updatedData.pool_questions.reading = updatedData.pool_questions.reading.filter(item => item.id !== id)
          updatedData.summary.reading_passages = updatedData.pool_questions.reading.length
        } else if (section === 'writing') {
          updatedData.pool_questions.writing = updatedData.pool_questions.writing.filter(item => item.id !== id)
          updatedData.summary.writing = updatedData.pool_questions.writing.length
        } else {
          const sectionKey = section as keyof typeof updatedData.pool_questions
          if (sectionKey in updatedData.pool_questions) {
            updatedData.pool_questions[sectionKey] = updatedData.pool_questions[sectionKey].filter(item => item.id !== id)
            // Update the corresponding summary field
            if (section === 'quantitative') {
              updatedData.summary.quantitative = updatedData.pool_questions[sectionKey].length
            } else if (section === 'analogy') {
              updatedData.summary.analogy = updatedData.pool_questions[sectionKey].length
            } else if (section === 'synonym') {
              updatedData.summary.synonym = updatedData.pool_questions[sectionKey].length
            }
          }
        }
        
        return updatedData
      })

      alert('Pool question deleted successfully!')
    } catch (err) {
      console.error('Error deleting pool question:', err)
      alert(`Failed to delete pool question: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDeletingId(null)
    }
  }

  const editPoolQuestion = (id: string) => {
    // Find the question in the data
    let question: PoolQuestion | null = null
    if (data?.pool_questions) {
      for (const section of Object.values(data.pool_questions)) {
        const found = section.find(item => item.id === id)
        if (found) {
          question = found
          break
        }
      }
    }
    
    if (question) {
      setEditingQuestion(question)
      setEditForm({
        question: question.question || '',
        choices: question.choices || [],
        answer: question.answer,
        explanation: question.explanation || '',
        difficulty: question.difficulty || '',
        prompt: question.prompt || '',
        passage: question.passage || '',
        tags: question.tags || []
      })
    }
  }

  const savePoolQuestion = async () => {
    if (!editingQuestion) return

    try {
      setEditingId(editingQuestion.id)
      const headers = await getAuthHeaders()
      
      // Determine the table based on the question type
      let tableName = ''
      let filteredUpdates: any = {}
      
      if (editingQuestion.passage) {
        tableName = 'ai_generated_reading_passages'
        // Only include fields that exist in ai_generated_reading_passages table
        filteredUpdates = {
          passage: editForm.passage,
          tags: editForm.tags
        }
      } else if (editingQuestion.prompt) {
        tableName = 'ai_generated_writing_prompts'
        // Only include fields that exist in ai_generated_writing_prompts table
        filteredUpdates = {
          prompt: editForm.prompt,
          tags: editForm.tags
        }
      } else {
        tableName = 'ai_generated_questions'
        // Only include fields that exist in ai_generated_questions table
        filteredUpdates = {
          question: editForm.question,
          choices: editForm.choices,
          answer: editForm.answer,
          explanation: editForm.explanation,
          difficulty: editForm.difficulty,
          tags: editForm.tags
        }
      }

      // Remove undefined/null values
      Object.keys(filteredUpdates).forEach(key => {
        if (filteredUpdates[key] === undefined || filteredUpdates[key] === null || filteredUpdates[key] === '') {
          delete filteredUpdates[key]
        }
      })

      const response = await fetch(`/api/admin/pool-questions/${editingQuestion.id}`, {
        method: 'PUT',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          table: tableName,
          updates: filteredUpdates
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to update pool question')
      }

      // Update local state
      setData(prev => {
        if (!prev) return prev
        
        const updatedData = { ...prev }
        const updatedQuestion = { ...editingQuestion, ...editForm }
        
        // Find and update the question in the appropriate section
        for (const [sectionKey, questions] of Object.entries(updatedData.pool_questions)) {
          const index = questions.findIndex(item => item.id === editingQuestion.id)
          if (index !== -1) {
            updatedData.pool_questions[sectionKey as keyof typeof updatedData.pool_questions][index] = updatedQuestion
            break
          }
        }
        
        return updatedData
      })

      alert('Pool question updated successfully!')
      setEditingQuestion(null)
      setEditForm({})
    } catch (err) {
      console.error('Error updating pool question:', err)
      alert(`Failed to update pool question: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setEditingId(null)
    }
  }

  const cancelEdit = () => {
    setEditingQuestion(null)
    setEditForm({})
  }

  const fetchPoolQuestions = async (section?: string) => {
    try {
      if (section) {
        setLoading(prev => ({ ...prev, [section]: true }))
      } else {
        setLoading(prev => ({ ...prev, all: true }))
      }
      
      setError(null)
      const headers = await getAuthHeaders()
      
      const urlParams = new URLSearchParams()
      if (section) urlParams.append('section', section)
      // Don't pass difficulty filter to API - we'll filter on frontend
      const url = `/api/admin/pool-questions${urlParams.toString() ? '?' + urlParams.toString() : ''}`
      const response = await fetch(url, {
        method: 'GET',
        headers,
      })

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access denied. Admin privileges required.')
        }
        const errorData = await response.json()
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const result = await response.json()
      
      if (section) {
        // Update specific section
        setUnfilteredData(prev => {
          if (!prev) {
            return {
              success: true,
              summary: {
                quantitative: 0,
                analogy: 0,
                synonym: 0,
                reading_passages: 0,
                reading_questions: 0,
                writing: 0
              },
              pool_questions: {
                quantitative: [],
                analogy: [],
                synonym: [],
                reading: [],
                writing: []
              }
            }
          }
          
          const updatedData = { ...prev }
          const sectionKey = section as keyof typeof updatedData.pool_questions
          if (sectionKey in updatedData.pool_questions) {
            updatedData.pool_questions[sectionKey] = result.pool_questions[sectionKey] || []
            // Update summary
            if (section === 'quantitative') {
              updatedData.summary.quantitative = updatedData.pool_questions[sectionKey].length
            } else if (section === 'analogy') {
              updatedData.summary.analogy = updatedData.pool_questions[sectionKey].length
            } else if (section === 'synonym') {
              updatedData.summary.synonym = updatedData.pool_questions[sectionKey].length
            } else if (section === 'reading') {
              updatedData.summary.reading_passages = updatedData.pool_questions[sectionKey].length
            } else if (section === 'writing') {
              updatedData.summary.writing = updatedData.pool_questions[sectionKey].length
            }
          }
          
          return updatedData
        })
        setLoadedSections(prev => new Set([...prev, section]))
      } else {
        // Load all sections - store unfiltered data
        setUnfilteredData(result)
        setLoadedSections(new Set(['quantitative', 'analogy', 'synonym', 'reading', 'writing']))
      }
    } catch (err) {
      console.error('Error fetching pool questions:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch pool questions')
    } finally {
      if (section) {
        setLoading(prev => ({ ...prev, [section]: false }))
      } else {
        setLoading(prev => ({ ...prev, all: false }))
      }
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(section)) {
        newSet.delete(section)
      } else {
        newSet.add(section)
      }
      return newSet
    })
  }

  const getSectionIcon = (section: string) => {
    switch (section) {
      case 'quantitative': return <Calculator className="w-5 h-5" />
      case 'analogy': return <Brain className="w-5 h-5" />
      case 'synonym': return <Brain className="w-5 h-5" />
      case 'reading': return <BookOpen className="w-5 h-5" />
      case 'writing': return <PenTool className="w-5 h-5" />
      default: return <FileText className="w-5 h-5" />
    }
  }

  const getSectionTitle = (section: string) => {
    switch (section) {
      case 'quantitative': return 'Quantitative Questions'
      case 'analogy': return 'Analogy Questions'
      case 'synonym': return 'Synonym Questions'
      case 'reading': return 'Reading Passages'
      case 'writing': return 'Writing Prompts'
      default: return section
    }
  }

  const renderQuestion = (question: PoolQuestion, index: number, section: string) => {
    return (
      <div key={question.id || index} className="bg-gray-50 p-4 rounded-lg mb-3">
        <div className="flex justify-between items-start mb-2">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-gray-600">Question {index + 1}</span>
            {question.id && (
              <div className="mt-1">
                {renderIdDisplay(question.id)}
              </div>
            )}
            {question.generation_session_id && (
              <div className="mt-1">
                <span className="text-xs text-gray-500">
                  Session: {question.generation_session_id}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {question.difficulty && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                {question.difficulty}
              </span>
            )}
            <div className="flex gap-1">
              <button
                onClick={(e) => {
                  e.preventDefault()
                  editPoolQuestion(question.id)
                }}
                disabled={editingId === question.id}
                className="text-gray-500 hover:text-blue-600 disabled:text-gray-300 transition-colors"
                title="Edit pool question"
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault()
                  deletePoolQuestion(question.id, section)
                }}
                disabled={deletingId === question.id}
                className="text-gray-500 hover:text-red-600 disabled:text-gray-300 transition-colors"
                title="Delete pool question"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        
        {question.question && (
          <div className="mb-3">
            <p className="text-gray-800 font-medium mb-2">{question.question}</p>
            {question.choices && question.choices.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                {question.choices.map((choice, i) => (
                  <li key={i} className={question.answer === i ? 'font-semibold text-green-700' : ''}>
                    {String.fromCharCode(65 + i)}. {choice}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        
        {question.explanation && (
          <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
            <strong>Explanation:</strong> {question.explanation}
          </div>
        )}
        
        {question.prompt && (
          <div className="text-sm text-gray-800">
            <div className="flex items-center gap-2 mb-1">
              <strong>Prompt:</strong>
              {question.id && renderIdDisplay(question.id)}
            </div>
            <div className="mt-1">{question.prompt}</div>
          </div>
        )}
        
        {question.passage && (
          <div className="text-sm text-gray-800 mb-2">
            <div className="flex items-center gap-2 mb-1">
              <strong>Passage:</strong>
              {question.id && renderIdDisplay(question.id)}
            </div>
            <div className="mt-1 p-3 bg-gray-100 rounded text-sm">
              {question.passage}
            </div>
          </div>
        )}

        {question.tags && question.tags.length > 0 && (
          <div className="mt-2">
            <div className="flex flex-wrap gap-1">
              {question.tags.map((tag, i) => (
                <span key={i} className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {question.created_at && (
          <div className="mt-2 text-xs text-gray-500">
            Created: {new Date(question.created_at).toLocaleString()}
          </div>
        )}
      </div>
    )
  }

  const sections = [
    { key: 'quantitative', title: 'Quantitative Questions' },
    { key: 'analogy', title: 'Analogy Questions' },
    { key: 'synonym', title: 'Synonym Questions' },
    { key: 'reading', title: 'Reading Passages' },
    { key: 'writing', title: 'Writing Prompts' }
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">
          {showChinese ? 'AI生成题库查看器' : 'Pool Questions Viewer'}
        </h2>
        <button
          onClick={() => fetchPoolQuestions()}
          disabled={loading.all}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md transition-colors"
        >
          {loading.all ? 'Loading...' : 'Load All Sections'}
        </button>
      </div>


      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{data?.summary.quantitative || 0}</div>
            <div className="text-sm text-gray-600">Quantitative</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{data?.summary.analogy || 0}</div>
            <div className="text-sm text-gray-600">Analogy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{data?.summary.synonym || 0}</div>
            <div className="text-sm text-gray-600">Synonym</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{data?.summary.reading_passages || 0}</div>
            <div className="text-sm text-gray-600">Reading Passages</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{data?.summary.reading_questions || 0}</div>
            <div className="text-sm text-gray-600">Reading Questions</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{data?.summary.writing || 0}</div>
            <div className="text-sm text-gray-600">Writing</div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {sections.map((section) => {
          const examples = data?.pool_questions[section.key as keyof typeof data.pool_questions] || []
          const isExpanded = expandedSections.has(section.key)
          const isLoading = loading[section.key]
          const isLoaded = loadedSections.has(section.key)

          return (
            <div key={section.key} className="bg-white rounded-lg shadow">
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => toggleSection(section.key)}
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                  {getSectionIcon(section.key)}
                  <span className="font-medium text-gray-900">{section.title}</span>
                  <span className="text-sm text-gray-500">({examples.length} questions)</span>
                </div>
                <div className="flex items-center gap-2">
                  {isLoaded && section.key !== 'writing' && (
                    <>
                      <select
                        value={sectionDifficultyFilters[section.key]}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          e.stopPropagation()
                          setSectionDifficultyFilters(prev => ({
                            ...prev,
                            [section.key]: e.target.value
                          }))
                        }}
                        className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">All</option>
                        <option value="Easy">Easy</option>
                        <option value="Medium">Medium</option>
                        <option value="Hard">Hard</option>
                      </select>
                      <button
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          // Reset filter to "All" and reload data
                          setSectionDifficultyFilters(prev => ({
                            ...prev,
                            [section.key]: ''
                          }))
                          fetchPoolQuestions(section.key)
                        }}
                        disabled={isLoading}
                        className="px-2 py-1 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white rounded transition-colors"
                        title="Reload data and reset filter"
                      >
                        ↻
                      </button>
                    </>
                  )}
                  {!isLoaded && (
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        fetchPoolQuestions(section.key)
                      }}
                      disabled={isLoading}
                      className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded transition-colors"
                    >
                      {isLoading ? 'Loading...' : 'Load'}
                    </button>
                  )}
                </div>
              </div>
              {isExpanded && (
                <div className="px-4 pb-4">
                  {examples.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      No pool questions available for this section
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {examples.map((question, index) => renderQuestion(question, index, section.key))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Edit Modal */}
      {editingQuestion && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Edit Pool Question
                </h3>
                <button
                  onClick={cancelEdit}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                {/* ID Display */}
                <div className="flex items-center gap-2">
                  <strong>ID:</strong>
                  {renderIdDisplay(editingQuestion.id)}
                </div>

                {/* Generation Session ID */}
                {editingQuestion.generation_session_id && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Generation Session ID
                    </label>
                    <input
                      type="text"
                      value={editingQuestion.generation_session_id}
                      disabled
                      className="w-full p-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
                    />
                  </div>
                )}

                {/* Question */}
                {editingQuestion.question && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Question
                    </label>
                    <textarea
                      value={editForm.question || ''}
                      onChange={(e) => setEditForm(prev => ({ ...prev, question: e.target.value }))}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      rows={3}
                    />
                  </div>
                )}

                {/* Choices */}
                {editingQuestion.choices && editingQuestion.choices.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Choices
                    </label>
                    <div className="space-y-2">
                      {editForm.choices?.map((choice, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <span className="w-6 text-sm font-medium text-gray-600">
                            {String.fromCharCode(65 + index)}.
                          </span>
                          <input
                            type="text"
                            value={choice}
                            onChange={(e) => {
                              const newChoices = [...(editForm.choices || [])]
                              newChoices[index] = e.target.value
                              setEditForm(prev => ({ ...prev, choices: newChoices }))
                            }}
                            className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Answer */}
                {editingQuestion.choices && editingQuestion.choices.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Correct Answer (0-based index)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max={(editForm.choices?.length || 1) - 1}
                      value={editForm.answer || 0}
                      onChange={(e) => setEditForm(prev => ({ ...prev, answer: parseInt(e.target.value) }))}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}

                {/* Explanation */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Explanation
                  </label>
                  <textarea
                    value={editForm.explanation || ''}
                    onChange={(e) => setEditForm(prev => ({ ...prev, explanation: e.target.value }))}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                  />
                </div>

                {/* Difficulty - only for ai_generated_questions */}
                {editingQuestion.question && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Difficulty
                    </label>
                    <select
                      value={editForm.difficulty || ''}
                      onChange={(e) => setEditForm(prev => ({ ...prev, difficulty: e.target.value }))}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Select difficulty</option>
                      <option value="Easy">Easy</option>
                      <option value="Medium">Medium</option>
                      <option value="Hard">Hard</option>
                    </select>
                  </div>
                )}

                {/* Prompt (for writing prompts) */}
                {editingQuestion.prompt && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Prompt
                    </label>
                    <textarea
                      value={editForm.prompt || ''}
                      onChange={(e) => setEditForm(prev => ({ ...prev, prompt: e.target.value }))}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      rows={4}
                    />
                  </div>
                )}

                {/* Passage (for reading passages) */}
                {editingQuestion.passage && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Passage
                    </label>
                    <textarea
                      value={editForm.passage || ''}
                      onChange={(e) => setEditForm(prev => ({ ...prev, passage: e.target.value }))}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      rows={6}
                    />
                  </div>
                )}

                {/* Tags */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editForm.tags?.join(', ') || ''}
                    onChange={(e) => setEditForm(prev => ({ 
                      ...prev, 
                      tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag)
                    }))}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="tag1, tag2, tag3"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={cancelEdit}
                  className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={savePoolQuestion}
                  disabled={editingId === editingQuestion.id}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md transition-colors"
                >
                  {editingId === editingQuestion.id ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
