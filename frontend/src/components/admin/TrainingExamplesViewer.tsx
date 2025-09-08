'use client'

import React, { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, BookOpen, Calculator, FileText, PenTool, Brain, Copy, Edit, Trash2 } from 'lucide-react'
import { getAuthHeaders } from '@/utils/auth'

interface TrainingExample {
  id: string
  question?: string
  choices?: string[]
  answer?: number
  explanation?: string
  difficulty?: string
  subsection?: string
  passage?: string
  passage_type?: string
  questions?: TrainingExample[]
  prompt?: string
  visual_description?: string
  tags?: string[]
  created_at?: string
}

interface TrainingExamplesData {
  success: boolean
  summary: {
    quantitative: number
    analogy: number
    synonym: number
    reading_passages: number
    reading_questions: number
    writing: number
  }
  training_examples: {
    quantitative: TrainingExample[]
    analogy: TrainingExample[]
    synonym: TrainingExample[]
    reading: TrainingExample[]
    writing: TrainingExample[]
  }
}

interface TrainingExamplesViewerProps {
  showChinese?: boolean
}

export function TrainingExamplesViewer({ showChinese = false }: TrainingExamplesViewerProps) {
  const [data, setData] = useState<TrainingExamplesData | null>(null)
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [loadedSections, setLoadedSections] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [editingExample, setEditingExample] = useState<TrainingExample | null>(null)
  const [editForm, setEditForm] = useState<Partial<TrainingExample>>({})
  const [sectionDifficultyFilters, setSectionDifficultyFilters] = useState<Record<string, string>>({
    quantitative: '',
    analogy: '',
    synonym: '',
    reading: '',
    writing: ''
  })
  const [unfilteredData, setUnfilteredData] = useState<TrainingExamplesData | null>(null) // Store unfiltered data

  // Effect to filter data when any section difficulty filter changes
  useEffect(() => {
    if (unfilteredData) {
      const filteredData = {
        ...unfilteredData,
        training_examples: {
          quantitative: sectionDifficultyFilters.quantitative 
            ? unfilteredData.training_examples.quantitative.filter(item => item.difficulty === sectionDifficultyFilters.quantitative)
            : unfilteredData.training_examples.quantitative,
          analogy: sectionDifficultyFilters.analogy 
            ? unfilteredData.training_examples.analogy.filter(item => item.difficulty === sectionDifficultyFilters.analogy)
            : unfilteredData.training_examples.analogy,
          synonym: sectionDifficultyFilters.synonym 
            ? unfilteredData.training_examples.synonym.filter(item => item.difficulty === sectionDifficultyFilters.synonym)
            : unfilteredData.training_examples.synonym,
          reading: sectionDifficultyFilters.reading 
            ? unfilteredData.training_examples.reading.map(passage => ({
                ...passage,
                questions: passage.questions?.filter(q => q.difficulty === sectionDifficultyFilters.reading) || []
              })).filter(passage => passage.questions && passage.questions.length > 0)
            : unfilteredData.training_examples.reading,
          writing: unfilteredData.training_examples.writing // Writing prompts don't have difficulty
        }
      }
      
      // Update summary counts
      filteredData.summary = {
        quantitative: filteredData.training_examples.quantitative.length,
        analogy: filteredData.training_examples.analogy.length,
        synonym: filteredData.training_examples.synonym.length,
        reading_passages: filteredData.training_examples.reading.length,
        reading_questions: filteredData.training_examples.reading.reduce((sum, passage) => sum + (passage.questions?.length || 0), 0),
        writing: filteredData.training_examples.writing.length
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

  const deleteTrainingExample = async (id: string, section: string) => {
    if (!confirm(`Are you sure you want to delete this training example?\n\nID: ${id}\n\nThis action cannot be undone.`)) {
      return
    }

    try {
      setDeletingId(id)
      const headers = await getAuthHeaders()
      
      // Determine the table based on section
      let tableName = ''
      if (section === 'reading') {
        tableName = 'reading_passages' // For reading, we delete the passage which cascades to questions
      } else if (section === 'writing') {
        tableName = 'writing_prompts'
      } else {
        tableName = 'ssat_questions'
      }

      const response = await fetch(`/api/admin/training-examples/${id}`, {
        method: 'DELETE',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ table: tableName })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to delete training example')
      }

      // Remove from local state (both filtered and unfiltered)
      const removeFromData = (data: TrainingExamplesData | null) => {
        if (!data) return data
        
        const updatedData = { ...data }
        if (section === 'reading') {
          updatedData.training_examples.reading = updatedData.training_examples.reading.filter(item => item.id !== id)
          updatedData.summary.reading_passages = updatedData.training_examples.reading.length
        } else if (section === 'writing') {
          updatedData.training_examples.writing = updatedData.training_examples.writing.filter(item => item.id !== id)
          updatedData.summary.writing = updatedData.training_examples.writing.length
        } else {
          const sectionKey = section as keyof typeof updatedData.training_examples
          if (sectionKey in updatedData.training_examples) {
            updatedData.training_examples[sectionKey] = updatedData.training_examples[sectionKey].filter(item => item.id !== id)
            // Update the corresponding summary field
            if (section === 'quantitative') {
              updatedData.summary.quantitative = updatedData.training_examples[sectionKey].length
            } else if (section === 'analogy') {
              updatedData.summary.analogy = updatedData.training_examples[sectionKey].length
            } else if (section === 'synonym') {
              updatedData.summary.synonym = updatedData.training_examples[sectionKey].length
            }
          }
        }
        
        return updatedData
      }
      
      setData(removeFromData)
      setUnfilteredData(removeFromData)

      alert('Training example deleted successfully!')
    } catch (err) {
      console.error('Error deleting training example:', err)
      alert(`Failed to delete training example: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDeletingId(null)
    }
  }

  const editTrainingExample = (id: string) => {
    // Find the example in the data
    let example: TrainingExample | null = null
    if (data?.training_examples) {
      for (const section of Object.values(data.training_examples)) {
        const found = section.find(item => item.id === id)
        if (found) {
          example = found
          break
        }
      }
    }
    
    if (example) {
      setEditingExample(example)
      setEditForm({
        question: example.question || '',
        choices: example.choices || [],
        answer: example.answer,
        explanation: example.explanation || '',
        difficulty: example.difficulty || '',
        prompt: example.prompt || '',
        passage: example.passage || '',
        tags: example.tags || []
      })
    }
  }

  const saveTrainingExample = async () => {
    if (!editingExample) return

    try {
      setEditingId(editingExample.id)
      const headers = await getAuthHeaders()
      
      // Determine the table based on the example type
      let tableName = ''
      let filteredUpdates: any = {}
      
      if (editingExample.passage) {
        tableName = 'reading_passages'
        // Only include fields that exist in reading_passages table
        filteredUpdates = {
          passage: editForm.passage,
          tags: editForm.tags
        }
      } else if (editingExample.prompt) {
        tableName = 'writing_prompts'
        // Only include fields that exist in writing_prompts table
        filteredUpdates = {
          prompt: editForm.prompt,
          tags: editForm.tags
        }
      } else {
        tableName = 'ssat_questions'
        // Only include fields that exist in ssat_questions table
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

      const response = await fetch(`/api/admin/training-examples/${editingExample.id}`, {
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
        throw new Error(errorData.error || 'Failed to update training example')
      }

      // Update local state (both filtered and unfiltered)
      const updateData = (data: TrainingExamplesData | null) => {
        if (!data) return data
        
        const updatedData = { ...data }
        const updatedExample = { ...editingExample, ...editForm }
        
        // Find and update the example in the appropriate section
        for (const [sectionKey, examples] of Object.entries(updatedData.training_examples)) {
          const index = examples.findIndex(item => item.id === editingExample.id)
          if (index !== -1) {
            updatedData.training_examples[sectionKey as keyof typeof updatedData.training_examples][index] = updatedExample
            break
          }
        }
        
        return updatedData
      }
      
      setData(updateData)
      setUnfilteredData(updateData)

      alert('Training example updated successfully!')
      setEditingExample(null)
      setEditForm({})
    } catch (err) {
      console.error('Error updating training example:', err)
      alert(`Failed to update training example: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setEditingId(null)
    }
  }

  const cancelEdit = () => {
    setEditingExample(null)
    setEditForm({})
  }

  const fetchTrainingExamples = async (section?: string) => {
    try {
      if (section) {
        setLoading(prev => ({ ...prev, [section]: true }))
      } else {
        setLoading({ all: true })
      }
      setError(null)
      
      const headers = await getAuthHeaders()
      const urlParams = new URLSearchParams()
      if (section) urlParams.append('section', section)
      // Don't pass difficulty filter to API - we'll filter on frontend
      const url = `/api/admin/training-examples${urlParams.toString() ? '?' + urlParams.toString() : ''}`
      
      console.log('🔍 FRONTEND: Fetching training examples with params:', {
        section,
        url
      })
      const response = await fetch(url, { headers })
      
      if (response.status === 403) {
        setError('Access denied. Admin privileges required.')
        return
      }
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to fetch training examples')
      }
      
      const result = await response.json()
      
      if (section) {
        // Update only the specific section
        setUnfilteredData(prev => {
          const currentData = prev || {
            success: true,
            summary: {
              quantitative: 0,
              analogy: 0,
              synonym: 0,
              reading_passages: 0,
              reading_questions: 0,
              writing: 0
            },
            training_examples: {
              quantitative: [],
              analogy: [],
              synonym: [],
              reading: [],
              writing: []
            }
          }
          
          return {
            ...currentData,
            success: true,
            summary: { ...currentData.summary, ...result.summary },
            training_examples: {
              ...currentData.training_examples,
              [section]: result.training_examples[section] || []
            }
          }
        })
        setLoadedSections(prev => new Set([...prev, section]))
      } else {
        // Load all sections - store unfiltered data
        setUnfilteredData(result)
        setLoadedSections(new Set(['quantitative', 'analogy', 'synonym', 'reading', 'writing']))
      }
    } catch (err) {
      console.error('Error fetching training examples:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch training examples')
    } finally {
      if (section) {
        setLoading(prev => ({ ...prev, [section]: false }))
      } else {
        setLoading({})
      }
    }
  }

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const getSectionIcon = (section: string) => {
    switch (section) {
      case 'quantitative': return <Calculator className="w-5 h-5" />
      case 'analogy': return <Brain className="w-5 h-5" />
      case 'synonym': return <FileText className="w-5 h-5" />
      case 'reading': return <BookOpen className="w-5 h-5" />
      case 'writing': return <PenTool className="w-5 h-5" />
      default: return <FileText className="w-5 h-5" />
    }
  }

  const getSectionTitle = (section: string) => {
    switch (section) {
      case 'quantitative': return 'Quantitative (Math)'
      case 'analogy': return 'Analogies'
      case 'synonym': return 'Synonyms'
      case 'reading': return 'Reading Comprehension'
      case 'writing': return 'Writing Prompts'
      default: return section
    }
  }

  const renderQuestion = (example: TrainingExample, index: number, section: string) => {
    return (
      <div key={example.id || index} className="bg-gray-50 p-4 rounded-lg mb-3">
        <div className="flex justify-between items-start mb-2">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-gray-600">Example {index + 1}</span>
            {example.id && (
              <div className="mt-1">
                {renderIdDisplay(example.id)}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {example.difficulty && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                {example.difficulty}
              </span>
            )}
            <div className="flex gap-1">
              <button
                onClick={(e) => {
                  e.preventDefault()
                  editTrainingExample(example.id)
                }}
                disabled={editingId === example.id}
                className="text-gray-500 hover:text-blue-600 disabled:text-gray-300 transition-colors"
                title="Edit training example"
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault()
                  deleteTrainingExample(example.id, section)
                }}
                disabled={deletingId === example.id}
                className="text-gray-500 hover:text-red-600 disabled:text-gray-300 transition-colors"
                title="Delete training example"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        
        {example.question && (
          <div className="mb-3">
            <p className="text-gray-800 font-medium mb-2">{example.question}</p>
            {example.choices && example.choices.length > 0 && (
              <div className="ml-4">
                {example.choices.map((choice, i) => (
                  <div key={i} className="flex items-center mb-1">
                    <span className="w-6 text-sm font-medium text-gray-600">
                      {String.fromCharCode(65 + i)}.
                    </span>
                    <span className={`text-sm ${
                      example.answer === i ? 'font-semibold text-green-600' : 'text-gray-700'
                    }`}>
                      {choice}
                    </span>
                    {example.answer === i && (
                      <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        Correct
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {example.explanation && (
          <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
            <strong>Explanation:</strong> {example.explanation}
          </div>
        )}
        
        {example.prompt && (
          <div className="text-sm text-gray-800">
            <div className="flex items-center gap-2 mb-1">
              <strong>Prompt:</strong>
              {example.id && renderIdDisplay(example.id)}
            </div>
            <div className="mt-1">{example.prompt}</div>
          </div>
        )}
        
        {example.passage && (
          <div className="text-sm text-gray-800 mb-2">
            <div className="flex items-center gap-2 mb-1">
              <strong>Passage:</strong>
              {example.id && renderIdDisplay(example.id)}
            </div>
            <div className="mt-1 p-3 bg-gray-100 rounded text-sm">
              {example.passage}
            </div>
          </div>
        )}
      </div>
    )
  }

  // Initialize data structure if not exists
  if (!data) {
    setData({
      success: true,
      summary: {
        quantitative: 0,
        analogy: 0,
        synonym: 0,
        reading_passages: 0,
        reading_questions: 0,
        writing: 0
      },
      training_examples: {
        quantitative: [],
        analogy: [],
        synonym: [],
        reading: [],
        writing: []
      }
    })
  }

  if (loading.all) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading all training examples...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <div className="text-red-600">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading training examples</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
            <button
              onClick={(e) => {
                e.preventDefault()
                fetchTrainingExamples()
              }}
              className="mt-2 text-sm bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center p-8 text-gray-500">
        No training examples data available
      </div>
    )
  }

  const sections = [
    { key: 'quantitative', title: 'Quantitative (Math)', count: data.summary.quantitative },
    { key: 'analogy', title: 'Analogies', count: data.summary.analogy },
    { key: 'synonym', title: 'Synonyms', count: data.summary.synonym },
    { key: 'reading', title: 'Reading Comprehension', count: data.summary.reading_passages },
    { key: 'writing', title: 'Writing Prompts', count: data.summary.writing }
  ]

  return (
    <div className="space-y-6">

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{data.summary.quantitative}</div>
            <div className="text-sm text-gray-600">Quantitative</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{data.summary.analogy}</div>
            <div className="text-sm text-gray-600">Analogy</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{data.summary.synonym}</div>
            <div className="text-sm text-gray-600">Synonym</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{data.summary.reading_passages}</div>
            <div className="text-sm text-gray-600">Reading Passages</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{data.summary.reading_questions}</div>
            <div className="text-sm text-gray-600">Reading Questions</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{data.summary.writing}</div>
            <div className="text-sm text-gray-600">Writing</div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={(e) => {
            e.preventDefault()
            fetchTrainingExamples()
          }}
          disabled={loading.all}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md transition-colors"
        >
          {loading.all ? 'Loading...' : 'Load All Sections'}
        </button>
      </div>

      <div className="space-y-4">
        {sections.map(section => {
          const examples = data.training_examples[section.key as keyof typeof data.training_examples] || []
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
                          fetchTrainingExamples(section.key)
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
                        fetchTrainingExamples(section.key)
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
                      No training examples available for this section
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {examples.map((example, index) => renderQuestion(example, index, section.key))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Edit Modal */}
      {editingExample && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Edit Training Example
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
                  {renderIdDisplay(editingExample.id)}
                </div>

                {/* Question */}
                {editingExample.question && (
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
                {editingExample.choices && editingExample.choices.length > 0 && (
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
                {editingExample.choices && editingExample.choices.length > 0 && (
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

                {/* Difficulty - only for ssat_questions */}
                {editingExample.question && (
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
                {editingExample.prompt && (
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
                {editingExample.passage && (
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
                  onClick={saveTrainingExample}
                  disabled={editingId === editingExample.id}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md transition-colors"
                >
                  {editingId === editingExample.id ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
