'use client'

import React, { useState, useEffect } from 'react'
import { Button } from './ui/Button'
import { TestSection, StandaloneSection, ReadingSection, WritingSection } from '@/types/api'
import { Eye, EyeOff, Download, CheckSquare } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { QuestionDisplay } from './QuestionDisplay'
import { generateUnifiedPDF } from '@/utils/pdfGenerator'

interface TestDisplayProps {
  sections: TestSection[]
  showChinese: boolean
}

export function TestDisplay({ sections, showChinese }: TestDisplayProps) {
  const [showAnswers, setShowAnswers] = useState(false)
  
  // Global interactive state for Check All Answers functionality
  const [globalUserAnswers, setGlobalUserAnswers] = useState<Array<{ questionId: string, selectedAnswer: string }>>([])
  const [globalShowResults, setGlobalShowResults] = useState(false)

  // Check if user has premium access for interactive features
  const { user } = useAuth()
  const hasPremiumAccess = user?.role === 'premium' || user?.role === 'admin'

  const handleDownloadCompleteTest = () => {
    generateUnifiedPDF(sections, {
      title: 'Complete SSAT Practice Test',
      includeAnswers: showAnswers,
      showSectionBreaks: true,
      language: showChinese ? 'zh' : 'en',
      testType: 'complete'
    })
  }

  const translations = {
    'Complete SmartSSAT Practice Test': '完整SmartSSAT练习测试',
    'Back to Home': '返回首页',
    'Download PDF': '下载PDF',
    'Print Test': '打印测试',
    'Loading test...': '加载测试中...',
    'Error loading test': '加载测试出错',
    'No test data available': '没有可用的测试数据'
  }


  if (sections.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h2 className="text-xl sm:text-2xl font-semibold text-gray-800">Complete SmartSSAT Test</h2>
            <p className="text-sm sm:text-base text-gray-600">{sections.length} sections</p>
          </div>
          
          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAnswers(!showAnswers)}
              className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
            >
              {showAnswers ? <EyeOff className="h-3 w-3 sm:h-4 sm:w-4" /> : <Eye className="h-3 w-3 sm:h-4 sm:w-4" />}
              <span className="whitespace-nowrap">{showAnswers ? 'Hide Answers' : 'Show Answers'}</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadCompleteTest}
              className="flex items-center justify-center space-x-2 text-xs sm:text-sm"
            >
              <Download className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="whitespace-nowrap">Save as PDF</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-8 p-6 pb-24">
        {sections.map((section, sectionIndex) => (
          <SectionWrapper
            key={sectionIndex}
            section={section}
            sectionIndex={sectionIndex}
            globalShowAnswers={showAnswers}
            setGlobalShowAnswers={setShowAnswers}
            globalUserAnswers={globalUserAnswers}
            setGlobalUserAnswers={setGlobalUserAnswers}
            globalShowResults={globalShowResults}
            setGlobalShowResults={setGlobalShowResults}
          />
        ))}
      </div>

      {/* Sticky Bottom Bar for Interactive Controls */}
      {hasPremiumAccess && (globalUserAnswers.length > 0 || globalShowResults) && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg z-50">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex items-center justify-center space-x-4">
              {/* Mode-based button display */}
              
              {/* Answer Mode: Check Answers */}
              {globalUserAnswers.length > 0 && !globalShowResults && (
                <Button
                  onClick={() => setGlobalShowResults(true)}
                  className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white"
                >
                  <CheckSquare className="h-4 w-4" />
                  <span>Check Answers</span>
                </Button>
              )}

              {/* Continue Answering Button */}
              {globalShowResults && (
                <Button
                  variant="outline"
                  onClick={() => setGlobalShowResults(false)}
                  className="flex items-center space-x-2"
                >
                  <span>Continue Answering</span>
                </Button>
              )}

              {/* Clear Answers Button */}
              {globalUserAnswers.length > 0 && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setGlobalUserAnswers([])
                    setGlobalShowResults(false)
                  }}
                  className="flex items-center space-x-2"
                >
                  <span>Clear Answers</span>
                </Button>
              )}

              {/* Total Score Display */}
              {globalShowResults && globalUserAnswers.length > 0 && (
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-700">Total Score:</span>
                  <span className="font-bold text-lg text-green-600">
                    {(() => {
                      let correct = 0
                      let total = 0
                      
                      sections.forEach(section => {
                        if (section.section_type === 'reading') {
                          section.passages.forEach(passage => {
                            passage.questions.forEach(question => {
                              total++
                              const userAnswer = globalUserAnswers.find(a => a.questionId === question.id)
                              if (userAnswer && userAnswer.selectedAnswer === question.correct_answer) {
                                correct++
                              }
                            })
                          })
                        } else if (section.section_type !== 'writing') {
                          (section as StandaloneSection).questions.forEach(question => {
                            total++
                            const userAnswer = globalUserAnswers.find(a => a.questionId === question.id)
                            if (userAnswer && userAnswer.selectedAnswer === question.correct_answer) {
                              correct++
                            }
                          })
                        }
                      })
                      
                      return `${correct}/${total}`
                    })()}
                  </span>
                </div>
              )}

              {/* Answer Count and Progress */}
              {globalUserAnswers.length > 0 && (
                <div className="text-sm text-gray-600">
                  {(() => {
                    let totalQuestions = 0
                    sections.forEach(section => {
                      if (section.section_type === 'reading') {
                        section.passages.forEach(passage => {
                          totalQuestions += passage.questions.length
                        })
                      } else if (section.section_type !== 'writing') {
                        totalQuestions += (section as StandaloneSection).questions.length
                      }
                    })
                    
                    return `${globalUserAnswers.length}/${totalQuestions} answered`
                  })()}
                  {globalShowResults && (
                    <span className="ml-2 text-green-600">
                      • {(() => {
                        let correct = 0
                        sections.forEach(section => {
                          if (section.section_type === 'reading') {
                            section.passages.forEach(passage => {
                              passage.questions.forEach(question => {
                                const userAnswer = globalUserAnswers.find(a => a.questionId === question.id)
                                if (userAnswer && userAnswer.selectedAnswer === question.correct_answer) {
                                  correct++
                                }
                              })
                            })
                          } else if (section.section_type !== 'writing') {
                            (section as StandaloneSection).questions.forEach(question => {
                              const userAnswer = globalUserAnswers.find(a => a.questionId === question.id)
                              if (userAnswer && userAnswer.selectedAnswer === question.correct_answer) {
                                correct++
                              }
                            })
                          }
                        })
                        return `${correct} correct`
                      })()}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StandaloneSectionDisplay({ section, showAnswers }: { section: StandaloneSection, showAnswers: boolean }) {
  const context = React.useContext(SectionStateContext)
  if (!context) throw new Error('StandaloneSectionDisplay must be used within SectionWrapper')
  
  const { userAnswers, setUserAnswers, showResults, setShowResults } = context
  
  return (
    <QuestionDisplay 
      questions={section.questions} 
      showChinese={false}
      showAnswers={showAnswers}
      showControls={false} // Don't show controls in QuestionDisplay since they're in the header
      showHeader={false}
      userAnswers={userAnswers}
      setUserAnswers={setUserAnswers}
      showResults={showResults}
      setShowResults={setShowResults}
    />
  )
}

function ReadingSectionDisplay({ section, showAnswers, setShowAnswers }: { section: ReadingSection, showAnswers: boolean, setShowAnswers: (show: boolean) => void }) {
  const context = React.useContext(SectionStateContext)
  if (!context) throw new Error('ReadingSectionDisplay must be used within SectionWrapper')
  
  const { userAnswers, setUserAnswers, showResults, setShowResults } = context
  return (
    <div className="space-y-8">
      {section.passages.map((passage, passageIndex) => (
        <div key={passage.id} className="border rounded-lg">
          <div className="bg-blue-50 p-4 border-b">
            <h4 className="font-semibold text-blue-900">{passage.title || `Passage ${passageIndex + 1}`}</h4>
            <p className="text-sm text-blue-700 capitalize">{passage.passage_type} • Grade {passage.grade_level}</p>
          </div>
          
          <div className="p-4">
            <div className="prose mb-6">
              <p className="text-gray-900 leading-relaxed whitespace-pre-wrap">{passage.text}</p>
            </div>
            
            <QuestionDisplay 
              questions={passage.questions} 
              showChinese={false}
              showAnswers={showAnswers}
              setShowAnswers={setShowAnswers}
              userAnswers={userAnswers}
              setUserAnswers={setUserAnswers}
              showResults={showResults}
              setShowResults={setShowResults}
              showControls={false}
              showHeader={false}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function WritingSectionDisplay({ section, showAnswers }: { section: WritingSection, showAnswers: boolean }) {
  const prompt = section.prompt
  
  // Debug logging
  console.log('🔍 WritingSectionDisplay Debug:', {
    imagePath: prompt.image_path,
    hasVisualDescription: !!prompt.visual_description,
    promptText: prompt.prompt_text?.substring(0, 50) + '...'
  });
  
  return (
    <div className="space-y-6">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
        
        <div className="space-y-4">
          <p className="text-purple-900 text-lg leading-relaxed">{prompt.prompt_text}</p>
          
          {/* Display image if available */}
          {prompt.image_path && (
            <div className="bg-purple-100 p-4 rounded border-l-4 border-purple-400">
              <div className="flex justify-center">
                <img 
                  src={`/images/${prompt.image_path}`}
                  alt="Writing prompt visual"
                  className="max-w-full max-h-96 rounded-lg shadow-md border-2 border-purple-200"
                  onError={(e) => {
                    console.warn('Failed to load image:', prompt.image_path);
                    e.currentTarget.style.display = 'none';
                  }}
                  onLoad={() => {
                    console.log('✅ Image loaded successfully:', prompt.image_path);
                  }}
                />
              </div>
            </div>
          )}
          
          {/* Display visual description if no image but description available */}
          {!prompt.image_path && prompt.visual_description && (
            <div className="bg-purple-100 p-3 rounded border-l-4 border-purple-400">
              <p className="text-sm text-purple-800">
                <strong>Visual Element:</strong> {prompt.visual_description}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Create a context to share section-level state between header and content
const SectionStateContext = React.createContext<{
  localOverride: boolean | null
  setLocalOverride: (value: boolean | null) => void
  userAnswers: Array<{ questionId: string, selectedAnswer: string }>
  setUserAnswers: (answers: Array<{ questionId: string, selectedAnswer: string }>) => void
  showResults: boolean
  setShowResults: (show: boolean) => void
} | null>(null)

function SectionWrapper({ 
  section, 
  sectionIndex, 
  globalShowAnswers,
  setGlobalShowAnswers,
  globalUserAnswers,
  setGlobalUserAnswers,
  globalShowResults,
  setGlobalShowResults
}: {
  section: TestSection,
  sectionIndex: number,
  globalShowAnswers: boolean,
  setGlobalShowAnswers: (show: boolean) => void,
  globalUserAnswers: Array<{ questionId: string, selectedAnswer: string }>,
  setGlobalUserAnswers: (answers: Array<{ questionId: string, selectedAnswer: string }>) => void,
  globalShowResults: boolean,
  setGlobalShowResults: (show: boolean) => void
}) {
  // Use 3-state: null (follow global), true (force show), false (force hide)
  const [localOverride, setLocalOverride] = useState<boolean | null>(null)
  
  // Interactive state for Check Answers functionality - sync with global state
  const [userAnswers, setUserAnswers] = useState<Array<{ questionId: string, selectedAnswer: string }>>([])
  const [showResults, setShowResults] = useState(false)
  
  // Sync local state with global state
  useEffect(() => {
    // Filter global answers for this section
    const sectionAnswers = globalUserAnswers.filter(answer => {
      // Check if this answer belongs to this section
      if (section.section_type === 'reading') {
        return section.passages.some(passage => 
          passage.questions.some((q: any) => q.id === answer.questionId)
        )
      } else if (section.section_type === 'writing') {
        // Writing sections don't have questions, so no answers
        return false
      } else {
        return (section as StandaloneSection).questions.some((q: any) => q.id === answer.questionId)
      }
    })
    setUserAnswers(sectionAnswers)
  }, [globalUserAnswers, section])
  
  // Sync local results with global results
  useEffect(() => {
    setShowResults(globalShowResults)
  }, [globalShowResults])
  
  // Update global state when local state changes
  const updateGlobalAnswers = (newAnswers: Array<{ questionId: string, selectedAnswer: string }>) => {
    setUserAnswers(newAnswers)
    
    // Remove old answers for this section from global state
    const otherSectionAnswers = globalUserAnswers.filter(answer => {
      if (section.section_type === 'reading') {
        return !section.passages.some(passage => 
          passage.questions.some((q: any) => q.id === answer.questionId)
        )
      } else if (section.section_type === 'writing') {
        // Writing sections don't have questions, so keep all answers
        return true
      } else {
        return !(section as StandaloneSection).questions.some((q: any) => q.id === answer.questionId)
      }
    })
    
    // Add new answers for this section
    setGlobalUserAnswers([...otherSectionAnswers, ...newAnswers])
  }
  
  return (
    <SectionStateContext.Provider value={{ 
      localOverride, 
      setLocalOverride,
      userAnswers,
      setUserAnswers: updateGlobalAnswers,
      showResults,
      setShowResults
    }}>
      <div className="border rounded-lg">
        <SectionHeader 
          section={section} 
          sectionIndex={sectionIndex}
          showAnswers={globalShowAnswers}
        />
                <SectionContent 
          section={section} 
          globalShowAnswers={globalShowAnswers}
          setGlobalShowAnswers={setGlobalShowAnswers}
          sectionIndex={sectionIndex}
        />
      </div>
    </SectionStateContext.Provider>
  )
}

function SectionHeader({ section, sectionIndex, showAnswers: globalShowAnswers }: { 
  section: TestSection, 
  sectionIndex: number,
  showAnswers: boolean 
}) {
  const context = React.useContext(SectionStateContext)
  if (!context) throw new Error('SectionHeader must be used within SectionWrapper')
  
  const { localOverride, setLocalOverride } = context
  
  // Clear 3-state logic:
  // - null: follow global setting
  // - true: force show (override global if global is false)
  // - false: force hide (override global if global is true)
  const effectiveShowAnswers = localOverride !== null ? localOverride : globalShowAnswers
  
  const getButtonText = () => {
    if (effectiveShowAnswers) {
      return 'Hide'
    } else {
      return 'Show'  
    }
  }
  
  const handleSectionToggle = () => {
    if (localOverride === null) {
      // No override currently, create one opposite to global
      setLocalOverride(!globalShowAnswers)
    } else {
      // Clear the override to go back to following global
      setLocalOverride(null)
    }
  }
  
  const handleSectionPDF = () => {
    generateUnifiedPDF([section], {
      title: `${section.section_type.charAt(0).toUpperCase() + section.section_type.slice(1)} Section`,
      includeAnswers: effectiveShowAnswers,
      showSectionBreaks: false,
      language: 'en', // TODO: Add language support to this component
      testType: 'complete'
    })
  }


  
  
  return (
    <div className="bg-gray-50 px-4 py-3 border-b">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold capitalize">{section.section_type} Section</h3>
          <p className="text-sm text-gray-600">
            {section.instructions}
          </p>
        </div>
        
        {/* Section-level controls (secondary) */}
        <div className="flex space-x-2">


          <Button
            variant="ghost"
            size="xs"
            onClick={handleSectionToggle}
            className="flex items-center space-x-1 text-xs"
          >
            {effectiveShowAnswers ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            <span>{getButtonText()}</span>
          </Button>
          
          <Button
            variant="ghost"
            size="xs"
            onClick={handleSectionPDF}
            className="flex items-center space-x-1 text-xs"
          >
            <Download className="h-3 w-3" />
            <span>PDF</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

function SectionContent({ section, globalShowAnswers, setGlobalShowAnswers, sectionIndex }: {
  section: TestSection,
  globalShowAnswers: boolean,
  setGlobalShowAnswers: (show: boolean) => void,
  sectionIndex: number
}) {
  const context = React.useContext(SectionStateContext)
  if (!context) throw new Error('SectionContent must be used within SectionWrapper')
  
  const { localOverride } = context
  
  // Use the same clear logic as SectionHeader
  const effectiveShowAnswers = localOverride !== null ? localOverride : globalShowAnswers
  
  return (
    <div className="p-4">
      {section.section_type === 'writing' ? (
        <WritingSectionDisplay section={section as WritingSection} showAnswers={effectiveShowAnswers} />
      ) : section.section_type === 'reading' ? (
        <ReadingSectionDisplay section={section as ReadingSection} showAnswers={effectiveShowAnswers} setShowAnswers={setGlobalShowAnswers} />
      ) : (
        <StandaloneSectionDisplay section={section as StandaloneSection} showAnswers={effectiveShowAnswers} />
      )}
    </div>
  )
}