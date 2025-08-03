'use client'

import { useState, useEffect } from 'react'
import { Button } from './ui/Button'
import { Question, ReadingPassage, QuestionOption } from '@/types/api'
import { Download, Eye, EyeOff, CheckSquare, CheckCircle, XCircle, Lock } from 'lucide-react'
import { generateUnifiedPDF } from '@/utils/pdfGenerator'
import { useAuth } from '@/contexts/AuthContext'

interface QuestionDisplayProps {
  questions?: Question[]
  passages?: ReadingPassage[]
  showChinese: boolean
  // Props for controlled behavior (when used as child component)
  showAnswers?: boolean      // External control of answer visibility
  setShowAnswers?: (show: boolean) => void  // External setter for showAnswers (optional)
  showControls?: boolean     // Whether to show the control buttons (default: true)
  showHeader?: boolean       // Whether to show the header section (default: true)
  showInteractiveControls?: boolean  // Whether to show interactive controls in header (default: true)
  // Props for external interactive state (when used in full test)
  userAnswers?: UserAnswer[]
  setUserAnswers?: (answers: UserAnswer[]) => void
  showResults?: boolean
  setShowResults?: (show: boolean) => void
}

interface UserAnswer {
  questionId: string
  selectedAnswer: string
}

export function QuestionDisplay({ 
  questions = [], 
  passages = [],
  showChinese, 
  showAnswers: externalShowAnswers,
  setShowAnswers: externalSetShowAnswers,
  showControls = true,
  showHeader = true,
  showInteractiveControls = true,
  userAnswers: externalUserAnswers,
  setUserAnswers: externalSetUserAnswers,
  showResults: externalShowResults,
  setShowResults: externalSetShowResults
}: QuestionDisplayProps) {
  // Internal state for standalone mode, external control for child mode
  const [internalShowAnswers, setInternalShowAnswers] = useState(false)
  
  // Use external control if provided, otherwise use internal state
  // For interactive mode, we want to allow it even when external showAnswers is true
  const showAnswers = externalShowAnswers !== undefined ? externalShowAnswers : internalShowAnswers
  
  // For interactive functionality, we need to distinguish between:
  // - externalShowAnswers: controlled by parent (full test global state)
  // - showResults: controlled by interactive Check Answers button
  // - userAnswers: user's selections for interactive mode

  // Use external interactive state if provided, otherwise use internal state
  const [internalUserAnswers, setInternalUserAnswers] = useState<UserAnswer[]>([])
  const [internalShowResults, setInternalShowResults] = useState(false)
  
  const userAnswers = externalUserAnswers !== undefined ? externalUserAnswers : internalUserAnswers
  const setUserAnswers = externalSetUserAnswers !== undefined ? externalSetUserAnswers : setInternalUserAnswers
  const showResults = externalShowResults !== undefined ? externalShowResults : internalShowResults
  const setShowResults = externalSetShowResults !== undefined ? externalSetShowResults : setInternalShowResults

  // Mode management for better UX
  const [mode, setMode] = useState<'answer' | 'results' | 'continue'>('answer')
  
  // Update mode based on state changes
  useEffect(() => {
    if (showResults && userAnswers.length > 0) {
      // Check if all questions are answered
      const allQuestions = questions.length + (passages?.reduce((total, passage) => total + passage.questions.length, 0) || 0)
      if (userAnswers.length === allQuestions) {
        setMode('results') // Complete results - all questions answered
      } else {
        setMode('continue') // Partial results - some questions answered
      }
    } else if (userAnswers.length > 0) {
      setMode('answer') // Answer mode - user has some answers but no results shown
    } else {
      setMode('answer') // Answer mode - no answers yet
    }
  }, [showResults, userAnswers.length, questions.length, passages])

  // Check if user has premium access for interactive features
  const { user } = useAuth()
  const hasPremiumAccess = user?.role === 'premium' || user?.role === 'admin'

  // UI translations mapping
  const translations = {
    // Header
    'Generated Questions': '生成的题目',
    'questions ready for practice': '道题目',
    'Show Answers': '显示答案',
    'Hide Answers': '隐藏答案', 
    'Save as PDF': '保存为PDF',
    'Print': '打印',
    'Section': '题',
    'Mixed Questions': '混合题目',
    
    // Question types
    'Quantitative': '数学',
    'Reading': '阅读',
    'Analogies': '类比',
    'Synonyms': '同义词',
    'Writing': '写作',
    
    // Question content
    'Question': '题目',
    'Correct Answer': '正确答案',
    'Explanation': '解析',
    'Visual Element': '图像元素',
    'Topics': '主题',
    'Answer Key': '答案',
    'Check Answers': '检查答案',
    'Reset Answers': '重置答案',
    'Correct!': '正确！',
    'Incorrect': '错误',
    
    // Premium feature messages
    'Interactive answer checking is a premium feature. Upgrade to Premium to select answers and check your work!': '交互式答题检查为高级功能。升级至高级版即可选择答案并检查您的答案！',
    'Interactive answer checking is a premium feature. Upgrade to Premium to check your answers!': '交互式答案检查是高级功能。升级到高级版以检查您的答案！',
    'Interactive answer checking is a premium feature. Upgrade to Premium to reset your answers!': '交互式答案检查是高级功能。升级到高级版以重置您的答案！',
    
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  // Handle user answer selection
  const handleAnswerClick = (questionId: string, selectedAnswer: string) => {
    if (!hasPremiumAccess) {
      // Show premium upgrade message
      alert(t('Interactive answer checking is a premium feature. Upgrade to Premium to select answers and check your work!'))
      return
    }
    
    // Prevent clicking when results are shown - user must hide results first
    if (showResults) {
      return
    }
    
    const newAnswers = userAnswers.filter((answer: UserAnswer) => answer.questionId !== questionId)
    setUserAnswers([...newAnswers, { questionId, selectedAnswer }])
  }

  // Get user's answer for a specific question
  const getUserAnswer = (questionId: string): UserAnswer | undefined => {
    return userAnswers.find(answer => answer.questionId === questionId)
  }

  // Get option styling based on user interaction
  const getOptionStyling = (questionId: string | undefined, optionLetter: string, correctAnswer: string) => {
    if (!questionId) {
      // Fallback styling when no question ID
      return showAnswers && optionLetter === correctAnswer
        ? 'border-green-500 bg-green-50'
        : 'border-gray-200 bg-gray-50'
    }
    
    const userAnswer = getUserAnswer(questionId)
    const isSelected = userAnswer?.selectedAnswer === optionLetter
    const isCorrect = optionLetter === correctAnswer
    
    if (showResults) {
      // Interactive results mode - highlight correct and incorrect answers
      // Only show results for questions that have been answered
      const userAnswer = getUserAnswer(questionId)
      if (userAnswer) {
        // This question was answered, show results
        if (isSelected) {
          return isCorrect 
            ? 'border-green-500 bg-green-50' 
            : 'border-red-500 bg-red-50'
        } else if (isCorrect) {
          // Show correct answer when user chose wrong
          return 'border-green-500 bg-green-50'
        } else {
          return 'border-gray-200 bg-gray-50'
        }
      } else {
        // This question was not answered, but results are shown so disable clicking
        return 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
      }
    } else if (userAnswers.length > 0) {
      // Interactive selection mode - highlight selected answers (takes priority over external showAnswers)
      if (isSelected) {
        return 'border-blue-500 bg-blue-50'
      } else {
        return 'border-gray-200 bg-gray-50 hover:bg-gray-100 cursor-pointer'
      }
    } else if (showAnswers) {
      // External show answers mode - highlight correct answer
      return isCorrect 
        ? 'border-green-500 bg-green-50' 
        : 'border-gray-200 bg-gray-50'
    } else {
      // No interaction yet - show as clickable only for premium users
      return hasPremiumAccess 
        ? 'border-gray-200 bg-gray-50 hover:bg-gray-100 cursor-pointer'
        : 'border-gray-200 bg-gray-50 opacity-60'
    }
  }

  // Handle check answers button
  const handleCheckAnswers = () => {
    if (!hasPremiumAccess) {
      alert(t('Interactive answer checking is a premium feature. Upgrade to Premium to check your answers!'))
      return
    }
    setShowResults(true)
  }

  // Handle continue answering button
  const handleContinueAnswering = () => {
    setShowResults(false)
  }

  // Handle reset answers button
  const handleResetAnswers = () => {
    if (!hasPremiumAccess) {
      alert(t('Interactive answer checking is a premium feature. Upgrade to Premium to reset your answers!'))
      return
    }
    setUserAnswers([])
    setShowResults(false)
    setMode('answer')
  }

  const handleDownload = () => {
    if (passages.length > 0) {
      // For reading comprehension, create structured content with passages
      const pdfContent: Question[] = []
      
      passages.forEach(passage => {
        // Add passage as a special question type
        pdfContent.push({
          id: `passage-${passage.id}`,
          question_type: 'passage',
          difficulty: 'Medium',
          text: passage.text,
          options: [],
          correct_answer: '',
          explanation: '',
          cognitive_level: 'READ',
          tags: ['reading', 'passage'],
          visual_description: undefined,
          metadata: { 
            isPassage: true, 
            title: passage.title,
            passage_type: passage.passage_type,
            passageText: passage.text
          }
        } as Question)
        
        // Add the questions for this passage
        passage.questions.forEach(question => {
          pdfContent.push({
            ...question,
            metadata: { 
              ...question.metadata, 
              isPassageQuestion: true,
              passageText: passage.text
            }
          })
        })
      })
      
      generateUnifiedPDF(pdfContent, {
        title: 'SSAT Practice Questions',
        includeAnswers: showAnswers,
        showSectionBreaks: false,
        language: showChinese ? 'zh' : 'en',
        testType: 'individual'
      })
    } else {
      // For standalone questions, use as-is
      generateUnifiedPDF(questions, {
        title: 'SSAT Practice Questions',
        includeAnswers: showAnswers,
        showSectionBreaks: false,
        language: showChinese ? 'zh' : 'en',
        testType: 'individual'
      })
    }
  }

  // Determine content type and counts
  const isReadingContent = passages.length > 0
  const totalQuestions = isReadingContent 
    ? passages.reduce((total, passage) => total + passage.questions.length, 0)
    : questions.length
  const contentCount = isReadingContent ? passages.length : questions.length

  if ((!questions || questions.length === 0) && (!passages || passages.length === 0)) {
    return null
  }

  return (
    <div className={showHeader ? "bg-white rounded-xl shadow-sm border border-gray-200" : ""}>
      {/* Header - Only show in standalone mode */}
      {showHeader && (
        <div className="border-b border-gray-200 p-4 sm:p-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-xl">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center space-y-4 sm:space-y-0">
            <div>
              {(() => {
                if (isReadingContent) {
                  // Reading comprehension
                  return (
                    <>
                      <h2 className="text-xl sm:text-2xl font-semibold text-gray-800">{t('Reading')} {t('Section')}</h2>
                      <p className="text-sm sm:text-base text-gray-600">
                        {contentCount} passage{contentCount > 1 ? 's' : ''} with {totalQuestions} {t('questions ready for practice')}
                      </p>
                    </>
                  )
                } else {
                  // Standalone questions
                  const questionTypes = [...new Set(questions.map(q => q.question_type))]
                  const sectionName = questionTypes.length === 1 
                    ? questionTypes[0] === 'quantitative' ? t('Quantitative') :
                      questionTypes[0] === 'analogy' ? t('Analogies') :
                      questionTypes[0] === 'synonym' ? t('Synonyms') :
                      questionTypes[0] === 'reading' ? t('Reading') :
                      questionTypes[0] === 'writing' ? t('Writing') :
                      questionTypes[0]
                    : t('Mixed Questions')
                  
                  return (
                    <>
                      <h2 className="text-xl sm:text-2xl font-semibold text-gray-800">{sectionName} {t('Section')}</h2>
                      <p className="text-sm sm:text-base text-gray-600">
                        {totalQuestions} {t('questions ready for practice')}
                        {userAnswers.length > 0 && (
                          <span className="ml-2 text-blue-600 font-medium">
                            • {userAnswers.length}/{totalQuestions} answered
                            {showResults && (
                              <span className="text-green-600">
                                • {userAnswers.filter(answer => {
                                  const question = questions.find(q => q.id === answer.questionId) || 
                                    passages.flatMap(p => p.questions).find(q => q.id === answer.questionId)
                                  return question && answer.selectedAnswer === question.correct_answer
                                }).length} correct
                              </span>
                            )}
                          </span>
                        )}
                      </p>
                    </>
                  )
                }
              })()}
            </div>
            
            {/* Controls in header - Only show in standalone mode */}
            {showControls && (
              <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
                {/* Interactive Controls - Only show in header if showInteractiveControls is true */}
                {showInteractiveControls && (
                  <>
                    {/* Answer Mode: Check Answers */}
                    {mode === 'answer' && userAnswers.length > 0 && (
                      <Button
                        size="sm"
                        onClick={handleCheckAnswers}
                        className="flex items-center justify-center space-x-2 text-xs sm:text-sm bg-green-600 hover:bg-green-700 text-white"
                      >
                        <CheckSquare className="h-3 w-3 sm:h-4 sm:w-4" />
                        <span className="whitespace-nowrap">{t('Check Answers')}</span>
                      </Button>
                    )}

                    {/* Continue Mode: Continue Answering (Partial Results) */}
                    {mode === 'continue' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleContinueAnswering}
                        className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
                      >
                        <span className="whitespace-nowrap">Hide Results</span>
                      </Button>
                    )}

                    {/* Results Mode: Continue Answering (Complete Results) */}
                    {mode === 'results' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleContinueAnswering}
                        className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
                      >
                        <span className="whitespace-nowrap">Hide Results</span>
                      </Button>
                    )}

                    {/* Reset Answers Button - Show when user has answers */}
                    {userAnswers.length > 0 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleResetAnswers}
                        className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
                      >
                        <span className="whitespace-nowrap">{t('Reset Answers')}</span>
                      </Button>
                    )}
                  </>
                )}

                {/* Basic Controls - Always show when showControls is true */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (externalSetShowAnswers) {
                      // Use external setter if provided (full test)
                      externalSetShowAnswers(!showAnswers)
                    } else {
                      // Use internal state if no external setter (custom section)
                      setInternalShowAnswers(!internalShowAnswers)
                    }
                  }}
                  className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
                >
                  {showAnswers ? <EyeOff className="h-3 w-3 sm:h-4 sm:w-4" /> : <Eye className="h-3 w-3 sm:h-4 sm:w-4" />}
                  <span className="whitespace-nowrap">{showAnswers ? t('Hide Answers') : t('Show Answers')}</span>
                </Button>
            
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
                >
                  <Download className="h-3 w-3 sm:h-4 sm:w-4" />
                  <span className="whitespace-nowrap">{t('Save as PDF')}</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      )}



      {/* Content List */}
      <div className={showHeader ? "p-6 space-y-8 print:p-4" : "space-y-8"}>
        {isReadingContent ? (
          // Reading comprehension: render passages with their questions
          passages.map((passage, passageIndex) => (
            <div key={passageIndex} className="space-y-6">
              {/* Passage Header and Text */}
              <div className="border-b border-gray-100 pb-6">
                <div className="mb-4">
                  <div className="flex items-center space-x-3 mb-3">
                    <span className="bg-green-100 text-green-800 text-sm font-medium px-2.5 py-0.5 rounded">
                      PASSAGE
                    </span>
                    <span className="bg-gray-100 text-gray-800 text-sm font-medium px-2.5 py-0.5 rounded capitalize">
                      {passage.passage_type || 'Reading'}
                    </span>
                    {passage.title && (
                      <span className="text-sm font-medium text-gray-600">
                        {passage.title}
                      </span>
                    )}
                  </div>
                </div>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-base text-gray-900 leading-relaxed">{passage.text}</p>
                </div>
              </div>
              
              {/* Questions for this passage */}
              {passage.questions.map((question: Question, questionIndex: number) => (
                <div key={questionIndex} className="border-b border-gray-100 last:border-b-0 pb-8 last:pb-0">
                  {/* Question Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded">
                          {t('Question')} {questionIndex + 1}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Question Text */}
                  <div className="mb-4">
                    <p className="text-lg text-gray-900 leading-relaxed">{question.text}</p>
                  </div>

                  {/* Visual Description */}
                  {question.visual_description && (
                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <p className="text-sm text-blue-800">
                        <strong>{t('Visual Element')}:</strong> {question.visual_description}
                      </p>
                    </div>
                  )}

                  {/* Options */}
                  <div className="space-y-2 mb-4">
                    {question.options.map((option: QuestionOption) => {
                      const userAnswer = question.id ? getUserAnswer(question.id) : undefined
                      const isSelected = userAnswer?.selectedAnswer === option.letter
                      const isCorrect = option.letter === question.correct_answer
                      
                      return (
                        <div 
                          key={option.letter} 
                          className={`p-3 rounded-lg border ${
                            getOptionStyling(question.id, option.letter, question.correct_answer)
                          }`}
                          onClick={() => question.id && handleAnswerClick(question.id, option.letter)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center">
                              <span className="font-medium text-gray-700 mr-3">{option.letter})</span>
                              <span className="text-gray-900">{option.text}</span>
                            </div>
                            {userAnswer && isSelected && showResults && (
                              <div className="ml-2">
                                {isCorrect ? (
                                  <CheckCircle className="h-5 w-5 text-green-600" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-red-600" />
                                )}
                              </div>
                            )}
                            {!hasPremiumAccess && !showAnswers && (
                              <div className="ml-2">
                                <Lock className="h-4 w-4 text-gray-400" />
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Answer and Explanation (when shown) */}
                  {(showAnswers || (showResults && question.id && getUserAnswer(question.id))) && (
                    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="mb-2">
                        <span className="font-semibold text-green-800">{t('Correct Answer')}: </span>
                        <span className="font-bold text-green-900">{question.correct_answer}</span>
                      </div>
                      {question.explanation && (
                        <div>
                          <span className="font-semibold text-green-800">{t('Explanation')}: </span>
                          <span className="text-green-900">{question.explanation}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Tags (only shown when answers are visible) */}
                  {showAnswers && question.tags && question.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {question.tags.map((tag: string, tagIndex: number) => (
                        <span 
                          key={tagIndex}
                          className="bg-indigo-100 text-indigo-800 text-xs font-medium px-2 py-1 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))
        ) : (
          // Standalone questions: render normally
          questions.map((question, index) => (
            <div key={index} className="border-b border-gray-100 last:border-b-0 pb-8 last:pb-0">
              {/* Question Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded">
                      {t('Question')} {index + 1}
                    </span>
                  </div>
                </div>
              </div>

              {/* Question Text */}
              <div className="mb-4">
                <p className="text-lg text-gray-900 leading-relaxed">{question.text}</p>
              </div>

              {/* Visual Description */}
              {question.visual_description && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>{t('Visual Element')}:</strong> {question.visual_description}
                  </p>
                </div>
              )}

              {/* Options */}
              {question.options && question.options.length > 0 && (
                <div className="space-y-2 mb-4">
                  {question.options.map((option) => {
                    const userAnswer = question.id ? getUserAnswer(question.id) : undefined
                    const isSelected = userAnswer?.selectedAnswer === option.letter
                    const isCorrect = option.letter === question.correct_answer
                    
                    return (
                      <div 
                        key={option.letter} 
                        className={`p-3 rounded-lg border ${
                          getOptionStyling(question.id, option.letter, question.correct_answer)
                        }`}
                        onClick={() => question.id && handleAnswerClick(question.id, option.letter)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <span className="font-medium text-gray-700 mr-3">{option.letter})</span>
                            <span className="text-gray-900">{option.text}</span>
                          </div>
                          {userAnswer && isSelected && showResults && (
                            <div className="ml-2">
                              {isCorrect ? (
                                <CheckCircle className="h-5 w-5 text-green-600" />
                              ) : (
                                <XCircle className="h-5 w-5 text-red-600" />
                              )}
                            </div>
                          )}
                          {!hasPremiumAccess && !showAnswers && (
                            <div className="ml-2">
                              <Lock className="h-4 w-4 text-gray-400" />
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Answer and Explanation (when shown) */}
              {(showAnswers || (showResults && question.id && getUserAnswer(question.id))) && question.correct_answer && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="mb-2">
                    <span className="font-semibold text-green-800">{t('Correct Answer')}: </span>
                    <span className="font-bold text-green-900">{question.correct_answer}</span>
                  </div>
                  {question.explanation && (
                    <div>
                      <span className="font-semibold text-green-800">{t('Explanation')}: </span>
                      <span className="text-green-900">{question.explanation}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Tags (only shown when answers are visible) */}
              {showAnswers && question.tags && question.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {question.tags.map((tag, tagIndex) => (
                    <span 
                      key={tagIndex}
                      className="bg-indigo-100 text-indigo-800 text-xs font-medium px-2 py-1 rounded"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Print-only Answer Key */}
      {!showAnswers && (
        <div className="hidden print:block p-6 border-t border-gray-200">
          <h3 className="text-xl font-semibold mb-4">{t('Answer Key')}</h3>
          <div className="grid grid-cols-5 gap-4">
            {isReadingContent ? (
              // For reading comprehension, show answers from all passage questions
              passages.flatMap(passage => passage.questions).map((question, questionIndex) => (
                <div key={questionIndex} className="text-center">
                  <span className="font-medium">{questionIndex + 1}. </span>
                  <span className="font-bold">{question.correct_answer}</span>
                </div>
              ))
            ) : (
              // For standalone questions, show answers normally
              questions.map((question, questionIndex) => (
                <div key={questionIndex} className="text-center">
                  <span className="font-medium">{questionIndex + 1}. </span>
                  <span className="font-bold">{question.correct_answer}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}