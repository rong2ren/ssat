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
    question_type: 'analogy' as const,
    difficulty: 'Medium' as const,
    topic: '',
    count: 5
  })
  const [countInput, setCountInput] = useState('5')

  // UI translations
  const translations = {
    'Question Type': '题目类型',
    'Difficulty': '难度',
    'Number of Questions': '题目数量',
    'Topic (Optional)': '主题（选填）',
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
    'Between 1-20 questions': '1-20道题目'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate count from current input (in case user didn't blur)
    const inputValue = parseInt(countInput) || 1
    const validCount = Math.max(1, Math.min(20, inputValue))
    
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
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

          {/* Difficulty */}
          <div className="space-y-2">
            <Label htmlFor="practice-difficulty">{t('Difficulty')} *</Label>
            <Select
              value={formData.difficulty}
              onChange={(value) => setFormData(prev => ({ ...prev, difficulty: value as any }))}
              options={difficulties}
              id="practice-difficulty"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Count */}
          <div className="space-y-2">
            <Label htmlFor="practice-count">{t('Number of Questions')} *</Label>
            <Input
              id="practice-count"
              type="number"
              min="1"
              max="20"
              value={countInput}
              onChange={(e) => setCountInput(e.target.value)}
              onBlur={() => {
                const value = parseInt(countInput) || 1
                const clampedValue = Math.max(1, Math.min(20, value))
                setCountInput(clampedValue.toString())
                setFormData(prev => ({ ...prev, count: clampedValue }))
              }}
            />
            <p className="text-xs text-gray-500">{t('Between 1-20 questions')}</p>
          </div>

          {/* Topic */}
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
        </div>

        {/* Submit Button */}
        <Button 
          type="submit" 
          disabled={loading}
          className="w-full md:w-auto"
          size="lg"
        >
          {loading ? t('Generating...') : t('Generate Practice Questions')}
        </Button>
      </form>
    </div>
  )
}