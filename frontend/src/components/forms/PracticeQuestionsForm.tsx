'use client'

import { useState } from 'react'
import { Button } from '../ui/Button'
import { Select } from '../ui/Select'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'
import { QuestionRequest } from '@/types/api'

interface PracticeQuestionsFormProps {
  onSubmit: (request: QuestionRequest) => void
  loading: boolean
  showChinese?: boolean
}

export function PracticeQuestionsForm({ onSubmit, loading, showChinese = false }: PracticeQuestionsFormProps) {
  const [formData, setFormData] = useState({
    question_type: 'analogy' as 'quantitative' | 'reading' | 'analogy' | 'synonym' | 'writing',
    difficulty: 'Medium' as const,
    topic: '',
    count: 1
  })
  const [countInput, setCountInput] = useState('1')

  // UI translations
  const translations = {
    'Question Type': '题目类型',
    'Difficulty': '难度',
    'Number of Questions': '题目数量',
    'Topic (Optional)': '主题',
    'Generate Single Section Practice Questions': '生成单项练习题目',
    'Generate Practice Questions': '生成练习题目',
    'Generating...': '生成中...',
    'Specify a topic to focus on (e.g., fractions, geometry, vocabulary)': '指定主题范围（例如：分数、几何、词汇）',
    'Quantitative': '数学',
    'Reading': '阅读',
    'Analogies': '类比',
    'Synonyms': '同义词',
    'Writing': '写作',
    'Easy': '简单',
    'Medium': '中等',
    'Hard': '困难',
    'Between 1-15 questions': '1-15道题目',
    'Number of Passages': '段落数量',
    'Between 1-3 passages (4 questions each)': '1-3篇（每篇4道题）'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate count from current input (in case user didn't blur)
    const inputValue = parseInt(countInput) || 1
    
    // Different validation for reading (passages) vs other sections (questions)
    let validCount: number
    if (formData.question_type === 'reading') {
      // For reading: 1-3 passages (each with 4 questions)
      validCount = Math.max(1, Math.min(3, inputValue))
    } else {
      // For other sections: 1-15 questions
      validCount = Math.max(1, Math.min(15, inputValue))
    }
    
    // Update the input display to show corrected value
    if (validCount.toString() !== countInput) {
      setCountInput(validCount.toString())
    }
    
    const request: QuestionRequest = {
      question_type: formData.question_type,
      difficulty: formData.difficulty,
      topic: formData.topic || undefined,
      count: validCount
    }
    
    onSubmit(request)
  }

  const questionTypes = [
    { value: 'quantitative', label: t('Quantitative') },
    { value: 'reading', label: t('Reading') },
    { value: 'analogy', label: t('Analogies') },
    { value: 'synonym', label: t('Synonyms') },
    { value: 'writing', label: t('Writing') }
  ]

  const difficulties = [
    { value: 'Easy', label: t('Easy') },
    { value: 'Medium', label: t('Medium') },
    { value: 'Hard', label: t('Hard') }
  ]

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          {t('Generate Single Section Practice Questions')}
        </h2>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-8">
        <div className={`grid grid-cols-1 gap-6 ${formData.question_type === 'writing' ? 'md:grid-cols-2' : 'md:grid-cols-3'}`}>
          {/* Question Type */}
          <div className="space-y-2">
            <Label htmlFor="practice-question-type">{t('Question Type')} *</Label>
            <Select
              value={formData.question_type}
              onChange={(value) => setFormData(prev => ({ ...prev, question_type: value as any }))}
              options={questionTypes}
              id="practice-question-type"
            />
          </div>

          {/* Difficulty - Hidden for writing */}
          {formData.question_type !== 'writing' && (
            <div className="space-y-2">
              <Label htmlFor="practice-difficulty">{t('Difficulty')} *</Label>
              <Select
                value={formData.difficulty}
                onChange={(value) => setFormData(prev => ({ ...prev, difficulty: value as any }))}
                options={difficulties}
                id="practice-difficulty"
              />
            </div>
          )}

          {/* Count */}
          <div className="space-y-2">
            <Label htmlFor="practice-count">
              {formData.question_type === 'reading' ? t('Number of Passages') : t('Number of Questions')} *
            </Label>
            <Input
              id="practice-count"
              type="number"
              min="1"
              max={formData.question_type === 'reading' ? 3 : 15}
              value={countInput}
              onChange={(e) => setCountInput(e.target.value)}
              onBlur={() => {
                const value = parseInt(countInput) || 1
                let clampedValue: number
                if (formData.question_type === 'reading') {
                  // For reading: 1-3 passages (each with 4 questions)
                  clampedValue = Math.max(1, Math.min(3, value))
                } else {
                  // For other sections: 1-15 questions
                  clampedValue = Math.max(1, Math.min(15, value))
                }
                setCountInput(clampedValue.toString())
                setFormData(prev => ({ ...prev, count: clampedValue }))
              }}
            />
            <p className="text-xs text-gray-500">
              {formData.question_type === 'reading' 
                ? t('Between 1-3 passages (4 questions each)') 
                : t('Between 1-15 questions')
              }
            </p>
          </div>
        </div>


        {/* <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <div className="space-y-2">
            <Label htmlFor="practice-topic">{t('Topic (Optional)')}</Label>
            <Input
              id="practice-topic"
              type="text"
              value={formData.topic}
              onChange={(e) => setFormData(prev => ({ ...prev, topic: e.target.value }))}
            />
            <p className="text-xs text-gray-500">
              {t('Specify a topic to focus on (e.g., fractions, geometry, vocabulary)')}
            </p>
          </div>
        </div> */}

        {/* Submit Button */}
        <div className="flex justify-center pt-6">
          <Button 
            type="submit" 
            disabled={loading}
            className="w-full sm:w-auto px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all duration-200"
            size="lg"
          >
            {loading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                {t('Generating...')}
              </div>
            ) : (
              <span className="whitespace-nowrap">{t('Generate Practice Questions')}</span>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}