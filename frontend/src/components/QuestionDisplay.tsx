'use client'

import { useState } from 'react'
import { Button } from './ui/Button'
import { Question, ReadingPassage, QuestionOption } from '@/types/api'
import { Download, Eye, EyeOff } from 'lucide-react'
import { generateUnifiedPDF } from '@/utils/pdfGenerator'

interface QuestionDisplayProps {
  questions?: Question[]
  passages?: ReadingPassage[]
  showChinese: boolean
  // Props for controlled behavior (when used as child component)
  showAnswers?: boolean      // External control of answer visibility
  showControls?: boolean     // Whether to show the control buttons (default: true)
  showHeader?: boolean       // Whether to show the header section (default: true)
}

export function QuestionDisplay({ 
  questions = [], 
  passages = [],
  showChinese, 
  showAnswers: externalShowAnswers,
  showControls = true,
  showHeader = true 
}: QuestionDisplayProps) {
  // Internal state for standalone mode, external control for child mode
  const [internalShowAnswers, setInternalShowAnswers] = useState(false)
  
  // Use external control if provided, otherwise use internal state
  const showAnswers = externalShowAnswers !== undefined ? externalShowAnswers : internalShowAnswers

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
    
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key


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
                      <p className="text-sm sm:text-base text-gray-600">{totalQuestions} {t('questions ready for practice')}</p>
                    </>
                  )
                }
              })()}
            </div>
            
            {/* Controls - Only show in standalone mode */}
            {showControls && (
              <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setInternalShowAnswers(!internalShowAnswers)}
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
                    {question.options.map((option: QuestionOption) => (
                      <div 
                        key={option.letter} 
                        className={`p-3 rounded-lg border ${
                          showAnswers && option.letter === question.correct_answer
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-200 bg-gray-50'
                        }`}
                      >
                        <span className="font-medium text-gray-700 mr-3">{option.letter})</span>
                        <span className="text-gray-900">{option.text}</span>
                      </div>
                    ))}
                  </div>

                  {/* Answer and Explanation (when shown) */}
                  {showAnswers && (
                    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="mb-2">
                        <span className="font-semibold text-green-800">{t('Correct Answer')}: </span>
                        <span className="font-bold text-green-900">{question.correct_answer}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-green-800">{t('Explanation')}: </span>
                        <span className="text-green-900">{question.explanation}</span>
                      </div>
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
                  {question.options.map((option) => (
                    <div 
                      key={option.letter} 
                      className={`p-3 rounded-lg border ${
                        showAnswers && option.letter === question.correct_answer
                          ? 'border-green-500 bg-green-50'
                          : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <span className="font-medium text-gray-700 mr-3">{option.letter})</span>
                      <span className="text-gray-900">{option.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Answer and Explanation (when shown) */}
              {showAnswers && question.correct_answer && (
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