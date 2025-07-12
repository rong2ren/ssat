'use client'

import { useState } from 'react'
import { Button } from './ui/Button'
import { Select } from './ui/Select'
import { Input } from './ui/Input'
import { Label } from './ui/Label'
import { QuestionRequest } from '@/types/api'

interface QuestionFormProps {
  onSubmit: (request: QuestionRequest) => void
  onGenerateCompleteTest: () => void
  loading: boolean
  showChinese: boolean
}

export function QuestionForm({ onSubmit, onGenerateCompleteTest, loading, showChinese }: QuestionFormProps) {
  const [formData, setFormData] = useState({
    question_type: 'math' as const,
    difficulty: 'Medium' as const,
    topic: '',
    count: 5
  })

  // UI translations for form
  const translations = {
    'Question Type': '题目类型',
    'Difficulty': '难度',
    'Number of Questions': '题目数量', 
    'Topic (Optional)': '主题（可选）',
    'Generate Questions': '生成题目',
    'Generate Complete Test': '生成完整测试',
    'Generating...': '生成中...',
    'Tips:': '提示：',
    'Individual Questions:': '单独题目：',
    'Complete Test:': '完整测试：',
    'Topics:': '主题：',
    'Print/Export:': '打印/导出：',
    'Generate 1-20 questions of a specific type': '生成1-20道特定类型的题目',
    'Generate a full SSAT practice test with multiple sections': '生成包含多个部分的完整SSAT练习测试',
    'Add topics like "fractions", "geometry", or "vocabulary" for focused practice': '添加"分数"、"几何"或"词汇"等主题进行针对性练习',
    'Generated questions are formatted for easy printing': '生成的题目格式便于打印',
    'Specify a topic to focus the questions on a particular subject area': '指定主题以将题目集中在特定学科领域'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const request: QuestionRequest = {
      question_type: formData.question_type,
      difficulty: formData.difficulty,
      topic: formData.topic || undefined,
      count: formData.count
    }
    
    onSubmit(request)
  }

  const questionTypes = [
    { value: 'math', label: 'Math' },
    { value: 'verbal', label: 'Verbal' },
    { value: 'reading', label: 'Reading Comprehension' },
    { value: 'analogy', label: 'Analogies' },
    { value: 'synonym', label: 'Synonyms' },
    { value: 'writing', label: 'Writing' }
  ]

  const difficulties = [
    { value: 'Easy', label: 'Easy' },
    { value: 'Medium', label: 'Medium' },
    { value: 'Hard', label: 'Hard' }
  ]


  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Question Type */}
        <div className="space-y-2">
          <Label htmlFor="question-type">{t('Question Type')}</Label>
          <Select
            value={formData.question_type}
            onChange={(value) => setFormData(prev => ({ ...prev, question_type: value as any }))}
            options={questionTypes}
            id="question-type"
          />
        </div>

        {/* Difficulty */}
        <div className="space-y-2">
          <Label htmlFor="difficulty">{t('Difficulty')}</Label>
          <Select
            value={formData.difficulty}
            onChange={(value) => setFormData(prev => ({ ...prev, difficulty: value as any }))}
            options={difficulties}
            id="difficulty"
          />
        </div>

        {/* Count */}
        <div className="space-y-2">
          <Label htmlFor="count">{t('Number of Questions')}</Label>
          <Input
            id="count"
            type="number"
            min="1"
            max="20"
            value={formData.count}
            onChange={(e) => setFormData(prev => ({ ...prev, count: parseInt(e.target.value) }))}
          />
        </div>

      </div>

      {/* Topic (full width) */}
      <div className="space-y-2">
        <Label htmlFor="topic">{t('Topic (Optional)')}</Label>
        <Input
          id="topic"
          type="text"
          placeholder="e.g., fractions, geometry, vocabulary..."
          value={formData.topic}
          onChange={(e) => setFormData(prev => ({ ...prev, topic: e.target.value }))}
        />
        <p className="text-sm text-gray-500">
          {t('Specify a topic to focus the questions on a particular subject area')}
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button 
          type="submit" 
          disabled={loading}
          className="flex-1"
        >
          {loading ? t('Generating...') : t('Generate Questions')}
        </Button>
        
        <Button 
          type="button"
          variant="outline"
          onClick={onGenerateCompleteTest}
          disabled={loading}
          className="flex-1"
        >
          {loading ? t('Generating...') : t('Generate Complete Test')}
        </Button>
      </div>

      <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-4">
        <p className="font-medium mb-2">💡 {t('Tips:')}</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>{t('Individual Questions:')}</strong> {t('Generate 1-20 questions of a specific type')}</li>
          <li><strong>{t('Complete Test:')}</strong> {t('Generate a full SSAT practice test with multiple sections')}</li>
          <li><strong>{t('Topics:')}</strong> {t('Add topics like "fractions", "geometry", or "vocabulary" for focused practice')}</li>
          <li><strong>{t('Print/Export:')}</strong> {t('Generated questions are formatted for easy printing')}</li>
        </ul>
      </div>
    </form>
  )
}