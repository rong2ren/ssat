'use client'

import { useState } from 'react'
import { QuestionDisplay } from '@/components/QuestionDisplay'
import { PracticeQuestionsForm } from '@/components/forms/PracticeQuestionsForm'
import { Question, QuestionRequest, ReadingPassage } from '@/types/api'

export default function CustomSectionPage() {
  const [questions, setQuestions] = useState<Question[]>([])
  const [passages, setPassages] = useState<ReadingPassage[]>([])
  const [contentType, setContentType] = useState<'questions' | 'passages' | 'prompts'>('questions')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // UI translations (for future language support)
  // const t = (key: string, showChinese: boolean = false) => key

  const handleGenerateQuestions = async (request: QuestionRequest) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }

      const data = await response.json()
      
      // Handle different response types based on content type
      if (data.questions) {
        // Standalone questions (math, verbal, analogy, synonym)
        setQuestions(data.questions)
        setPassages([])
        setContentType('questions')
      } else if (data.passages) {
        // Reading comprehension - keep passages in their natural structure
        setPassages(data.passages)
        setQuestions([])
        setContentType('passages')
      } else if (data.prompts) {
        // Writing prompts - convert to question-like format for display
        const promptQuestions = data.prompts.map((prompt: { prompt_text: string; visual_description?: string; instructions: string }, index: number) => ({
          id: `writing-${index}`,
          question_type: 'writing',
          difficulty: request.difficulty,
          text: prompt.prompt_text, // Just the prompt, not combined with instructions
          options: [], // No options for writing
          correct_answer: '',
          explanation: 'This is a creative writing task. Write a story with a beginning, middle, and end.',
          cognitive_level: 'CREATE',
          tags: ['writing', 'creative'],
          visual_description: prompt.visual_description || undefined,
          metadata: {
            isWritingPrompt: true,
            instructions: prompt.instructions
          }
        }))
        setQuestions(promptQuestions)
        setPassages([])
        setContentType('prompts')
      } else {
        throw new Error('Invalid response format')
      }
      
    } catch (err) {
      console.error('Failed to generate questions:', err)
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-12">
        {/* Page Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Custom Section Practice
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Generate targeted practice questions for specific SSAT sections
          </p>
        </div>

        <div className="max-w-6xl mx-auto space-y-8">
          {/* Practice Questions Form */}
          <PracticeQuestionsForm
            onSubmit={handleGenerateQuestions}
            loading={loading}
            showChinese={false} // Can add language toggle later if needed
          />

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <div className="flex items-center">
                <div className="text-red-600 font-medium">
                  Error generating questions
                </div>
              </div>
              <p className="text-red-700 mt-2">{error}</p>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12">
              <div className="flex flex-col items-center justify-center text-center">
                <div className="relative mb-6">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
                  <div className="absolute inset-0 rounded-full bg-blue-100 opacity-20"></div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Generating questions...
                </h3>
                <p className="text-gray-600 max-w-md">
                  Our AI is creating personalized SSAT questions based on your requirements. This may take a few moments.
                </p>
                <div className="mt-6 flex items-center space-x-2 text-sm text-gray-500">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span>Processing...</span>
                </div>
              </div>
            </div>
          )}

          {/* Results Display */}
          {!loading && (
            <>
              {contentType === 'questions' && questions.length > 0 && (
                <QuestionDisplay questions={questions} showChinese={false} />
              )}
              {contentType === 'passages' && passages.length > 0 && (
                <QuestionDisplay passages={passages} showChinese={false} />
              )}
              {contentType === 'prompts' && questions.length > 0 && (
                <QuestionDisplay questions={questions} showChinese={false} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}