'use client'

import { useState } from 'react'
import { Button } from './ui/Button'
import { TestSection, StandaloneSection, ReadingSection, WritingSection } from '@/types/api'
import { Download, Printer, Eye, EyeOff } from 'lucide-react'
import { QuestionDisplay } from './QuestionDisplay'

interface TestDisplayProps {
  sections: TestSection[]
  showChinese: boolean
}

export function TestDisplay({ sections, showChinese }: TestDisplayProps) {
  const [showAnswers, setShowAnswers] = useState(false)

  const t = (key: string) => key // Simplified for now

  const handlePrint = () => {
    window.print()
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
            <p className="text-gray-600">{sections.length} sections • Interactive practice test</p>
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
              size="sm"
              onClick={handlePrint}
              className="flex items-center space-x-2"
            >
              <Printer className="h-4 w-4" />
              <span>Print</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-8 p-6">
        {sections.map((section, sectionIndex) => (
          <div key={sectionIndex} className="border rounded-lg">
            <div className="bg-gray-50 px-4 py-3 border-b">
              <h3 className="text-lg font-semibold capitalize">{section.section_type} Section</h3>
              <p className="text-sm text-gray-600">
                Time limit: {section.time_limit_minutes} minutes • {section.instructions}
              </p>
            </div>
            
            <div className="p-4">
              {section.section_type === 'writing' ? (
                <WritingSectionDisplay section={section as WritingSection} showAnswers={showAnswers} />
              ) : section.section_type === 'reading' ? (
                <ReadingSectionDisplay section={section as ReadingSection} showAnswers={showAnswers} />
              ) : (
                <StandaloneSectionDisplay section={section as StandaloneSection} showAnswers={showAnswers} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StandaloneSectionDisplay({ section, showAnswers }: { section: StandaloneSection, showAnswers: boolean }) {
  return <QuestionDisplay questions={section.questions} showChinese={false} />
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
            
            <QuestionDisplay questions={passage.questions} showChinese={false} />
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