'use client'

import React, { useState } from 'react'
import { Button } from './ui/Button'
import { TestSection, StandaloneSection, ReadingSection, WritingSection } from '@/types/api'
import { Eye, EyeOff, Download } from 'lucide-react'
import { QuestionDisplay } from './QuestionDisplay'

interface TestDisplayProps {
  sections: TestSection[]
  showChinese: boolean
}

export function TestDisplay({ sections, showChinese }: TestDisplayProps) {
  const [showAnswers, setShowAnswers] = useState(false)

  const t = (key: string) => key // Simplified for now

  const handleDownloadCompleteTest = () => {
    // Collect all questions from all sections
    const allQuestions: any[] = []
    
    sections.forEach((section, sectionIndex) => {
      if (section.section_type === 'writing') {
        // Add writing prompt as a special "question"
        const writingSection = section as WritingSection
        allQuestions.push({
          text: `Writing Prompt: ${writingSection.prompt.prompt_text}`,
          options: [],
          correct_answer: '',
          explanation: writingSection.prompt.instructions,
          cognitive_level: 'Creative',
          tags: ['writing'],
          sectionName: 'Writing'
        })
      } else if (section.section_type === 'reading') {
        const readingSection = section as ReadingSection
        readingSection.passages.forEach((passage, passageIndex) => {
          // Add passage text as context
          allQuestions.push({
            text: `Reading Passage ${passageIndex + 1}: ${passage.title || 'Untitled'}`,
            options: [],
            correct_answer: '',
            explanation: passage.text,
            cognitive_level: 'Comprehension',
            tags: ['reading', 'passage'],
            sectionName: 'Reading'
          })
          // Add passage questions
          passage.questions.forEach(q => {
            allQuestions.push({
              ...q,
              sectionName: 'Reading'
            })
          })
        })
      } else {
        // Standalone sections (quantitative, analogy, synonym)
        const standaloneSection = section as StandaloneSection
        standaloneSection.questions.forEach(q => {
          allQuestions.push({
            ...q,
            sectionName: section.section_type
          })
        })
      }
    })

    // Generate PDF with all questions
    generateCompletePDF(allQuestions, showAnswers)
  }

  const generateCompletePDF = (questions: any[], includeAnswers: boolean) => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    
    const content = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Complete SSAT Practice Test - ${new Date().toISOString().split('T')[0]}</title>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
            .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 15px; }
            .section-break { page-break-before: always; margin-top: 40px; padding-top: 20px; border-top: 3px solid #2563eb; }
            .question { margin-bottom: 30px; page-break-inside: avoid; }
            .question-number { font-weight: bold; color: #2563eb; }
            .options { margin: 15px 0; }
            .option { margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; }
            .answer-section { margin-top: 15px; padding: 15px; background: #dcfce7; border-radius: 6px; border-left: 4px solid #16a34a; }
            .passage { background: #dbeafe; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2563eb; }
            @media print { 
              body { margin: 20px; } 
              .question { page-break-inside: avoid; }
              .section-break { page-break-before: always; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Complete SSAT Practice Test</h1>
            <p>Generated on ${new Date().toLocaleDateString()}</p>
            <p>${questions.length} questions • ${includeAnswers ? 'With Answer Key' : 'Questions Only'}</p>
          </div>
          ${questions.map((question, index) => {
            const isNewSection = index === 0 || question.sectionName !== questions[index - 1]?.sectionName
            return `
              ${isNewSection ? `<div class="section-break"><h2>${question.sectionName} Section</h2></div>` : ''}
              <div class="question">
                <div class="question-number">Question ${index + 1}</div>
                ${question.sectionName === 'Reading' && question.tags?.includes('passage') ? 
                  `<div class="passage"><strong>Reading Passage:</strong><br>${question.explanation}</div>` :
                  `<p><strong>${question.text}</strong></p>`
                }
                ${question.options && question.options.length > 0 ? `
                  <div class="options">
                    ${question.options.map((option: any) => 
                      `<div class="option">${option.letter}. ${option.text}</div>`
                    ).join('')}
                  </div>
                ` : ''}
                ${includeAnswers ? `
                  <div class="answer-section">
                    <strong>Answer:</strong> ${question.correct_answer}<br>
                    <strong>Explanation:</strong> ${question.explanation}
                  </div>
                ` : ''}
              </div>
            `
          }).join('')}
          ${!includeAnswers ? `
            <div style="page-break-before: always; margin-top: 40px;">
              <h2>Answer Key</h2>
              <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;">
                ${questions.map((question, index) => `
                  <div style="text-align: center; padding: 8px; background: #f3f4f6; border-radius: 4px;">
                    <strong>${index + 1}.</strong> ${question.correct_answer}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </body>
      </html>
    `
    
    printWindow.document.write(content)
    printWindow.document.close()
    printWindow.focus()
    setTimeout(() => {
      printWindow.print()
      printWindow.close()
    }, 250)
  }

  if (sections.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-gray-800">Complete SSAT Test</h2>
            <p className="text-gray-600">{sections.length} sections</p>
          </div>
          
          <div className="flex space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAnswers(!showAnswers)}
              className="flex items-center space-x-2"
            >
              {showAnswers ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              <span>{showAnswers ? 'Hide Answers' : 'Show Answers'}</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadCompleteTest}
              className="flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>Save Complete Test as PDF</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-8 p-6">
        {sections.map((section, sectionIndex) => (
          <SectionWrapper
            key={sectionIndex}
            section={section}
            sectionIndex={sectionIndex}
            globalShowAnswers={showAnswers}
          />
        ))}
      </div>
    </div>
  )
}

function StandaloneSectionDisplay({ section, showAnswers }: { section: StandaloneSection, showAnswers: boolean }) {
  return (
    <QuestionDisplay 
      questions={section.questions} 
      showChinese={false}
      showAnswers={showAnswers}
      showControls={false}
      showHeader={false}
    />
  )
}

function ReadingSectionDisplay({ section, showAnswers }: { section: ReadingSection, showAnswers: boolean }) {
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
  
  return (
    <div className="space-y-6">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
        <h4 className="text-lg font-semibold text-purple-900 mb-3">Writing Prompt</h4>
        
        <div className="space-y-4">
          <p className="text-purple-900 text-lg leading-relaxed">{prompt.prompt_text}</p>
          
          {prompt.visual_description && (
            <div className="bg-purple-100 p-3 rounded border-l-4 border-purple-400">
              <p className="text-sm text-purple-800">
                <strong>Visual Element:</strong> {prompt.visual_description}
              </p>
            </div>
          )}
          
          <div className="bg-white p-4 border border-purple-200 rounded">
            <p className="text-sm text-purple-900 mb-2">
              <strong>Instructions:</strong> {prompt.instructions}
            </p>
            
            {prompt.story_elements && prompt.story_elements.length > 0 && (
              <div className="mt-3">
                <p className="text-sm text-purple-800 mb-2"><strong>Story Elements to Consider:</strong></p>
                <div className="flex flex-wrap gap-2">
                  {prompt.story_elements.map((element, index) => (
                    <span key={index} className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded">
                      {element}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <div className="bg-gray-50 p-4 border rounded">
            <p className="text-sm text-gray-600 italic">
              [Student would write their story here during the actual test]
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Create a context to share section-level state between header and content
const SectionStateContext = React.createContext<{
  localOverride: boolean | null
  setLocalOverride: (value: boolean | null) => void
} | null>(null)

function SectionWrapper({ section, sectionIndex, globalShowAnswers }: {
  section: TestSection,
  sectionIndex: number,
  globalShowAnswers: boolean
}) {
  // Use 3-state: null (follow global), true (force show), false (force hide)
  const [localOverride, setLocalOverride] = useState<boolean | null>(null)
  
  return (
    <SectionStateContext.Provider value={{ localOverride, setLocalOverride }}>
      <div className="border rounded-lg">
        <SectionHeader 
          section={section} 
          sectionIndex={sectionIndex}
          showAnswers={globalShowAnswers}
        />
        <SectionContent 
          section={section}
          globalShowAnswers={globalShowAnswers}
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
    // Generate PDF for this specific section
    const sectionQuestions: any[] = []
    
    if (section.section_type === 'writing') {
      const writingSection = section as WritingSection
      sectionQuestions.push({
        text: `Writing Prompt: ${writingSection.prompt.prompt_text}`,
        options: [],
        correct_answer: '',
        explanation: writingSection.prompt.instructions,
        cognitive_level: 'Creative',
        tags: ['writing'],
        sectionName: 'Writing'
      })
    } else if (section.section_type === 'reading') {
      const readingSection = section as ReadingSection
      readingSection.passages.forEach((passage, passageIndex) => {
        sectionQuestions.push({
          text: `Reading Passage ${passageIndex + 1}: ${passage.title || 'Untitled'}`,
          options: [],
          correct_answer: '',
          explanation: passage.text,
          cognitive_level: 'Comprehension',
          tags: ['reading', 'passage'],
          sectionName: 'Reading'
        })
        passage.questions.forEach(q => {
          sectionQuestions.push({
            ...q,
            sectionName: 'Reading'
          })
        })
      })
    } else {
      const standaloneSection = section as StandaloneSection
      standaloneSection.questions.forEach(q => {
        sectionQuestions.push({
          ...q,
          sectionName: section.section_type
        })
      })
    }
    
    generateSectionPDF(sectionQuestions, effectiveShowAnswers, section.section_type)
  }
  
  const generateSectionPDF = (questions: any[], includeAnswers: boolean, sectionType: string) => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    
    const content = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${sectionType.charAt(0).toUpperCase() + sectionType.slice(1)} Section - ${new Date().toISOString().split('T')[0]}</title>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
            .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 15px; }
            .question { margin-bottom: 30px; page-break-inside: avoid; }
            .question-number { font-weight: bold; color: #2563eb; }
            .options { margin: 15px 0; }
            .option { margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; }
            .answer-section { margin-top: 15px; padding: 15px; background: #dcfce7; border-radius: 6px; border-left: 4px solid #16a34a; }
            .passage { background: #dbeafe; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2563eb; }
            @media print { 
              body { margin: 20px; } 
              .question { page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>${sectionType.charAt(0).toUpperCase() + sectionType.slice(1)} Section</h1>
            <p>Generated on ${new Date().toLocaleDateString()}</p>
            <p>${questions.length} questions • ${includeAnswers ? 'With Answer Key' : 'Questions Only'}</p>
          </div>
          ${questions.map((question, index) => `
            <div class="question">
              <div class="question-number">Question ${index + 1}</div>
              ${question.sectionName === 'Reading' && question.tags?.includes('passage') ? 
                `<div class="passage"><strong>Reading Passage:</strong><br>${question.explanation}</div>` :
                `<p><strong>${question.text}</strong></p>`
              }
              ${question.options && question.options.length > 0 ? `
                <div class="options">
                  ${question.options.map((option: any) => 
                    `<div class="option">${option.letter}. ${option.text}</div>`
                  ).join('')}
                </div>
              ` : ''}
              ${includeAnswers ? `
                <div class="answer-section">
                  <strong>Answer:</strong> ${question.correct_answer}<br>
                  <strong>Explanation:</strong> ${question.explanation}
                </div>
              ` : ''}
            </div>
          `).join('')}
          ${!includeAnswers ? `
            <div style="page-break-before: always; margin-top: 40px;">
              <h2>Answer Key</h2>
              <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;">
                ${questions.map((question, index) => `
                  <div style="text-align: center; padding: 8px; background: #f3f4f6; border-radius: 4px;">
                    <strong>${index + 1}.</strong> ${question.correct_answer}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </body>
      </html>
    `
    
    printWindow.document.write(content)
    printWindow.document.close()
    printWindow.focus()
    setTimeout(() => {
      printWindow.print()
      printWindow.close()
    }, 250)
  }
  
  return (
    <div className="bg-gray-50 px-4 py-3 border-b">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold capitalize">{section.section_type} Section</h3>
          <p className="text-sm text-gray-600">
            Time limit: {section.time_limit_minutes} minutes • {section.instructions}
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

function SectionContent({ section, globalShowAnswers, sectionIndex }: {
  section: TestSection,
  globalShowAnswers: boolean,
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
        <ReadingSectionDisplay section={section as ReadingSection} showAnswers={effectiveShowAnswers} />
      ) : (
        <StandaloneSectionDisplay section={section as StandaloneSection} showAnswers={effectiveShowAnswers} />
      )}
    </div>
  )
}