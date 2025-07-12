'use client'

import { useState } from 'react'
import { Button } from './ui/Button'
import { Select } from './ui/Select'
import { Input } from './ui/Input'
import { Label } from './ui/Label'
import { QuestionRequest } from '@/types/api'

interface QuestionFormProps {
  onSubmit: (request: QuestionRequest) => void
  onGenerateCompleteTest: (customConfig?: {
    sections: string[]
    counts: Record<string, number>
    difficulty: string
  }) => void
  loading: boolean
  showChinese: boolean
}

export function QuestionForm({ onSubmit, onGenerateCompleteTest, loading, showChinese }: QuestionFormProps) {
  const [formData, setFormData] = useState({
    question_type: 'analogy' as const,
    difficulty: 'Medium' as const,
    topic: '',
    count: 5
  })

  // Complete test customization state
  const [showCustomization, setShowCustomization] = useState(false)
  const [selectedSections, setSelectedSections] = useState(['quantitative', 'reading', 'analogy', 'synonym', 'writing'])
  const [customCounts, setCustomCounts] = useState({
    quantitative: 10,
    reading: 7,
    analogy: 5,
    synonym: 5,
    writing: 1
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
    'Customize Complete Test': '自定义完整测试',
    'Select Sections': '选择部分',
    'Questions per Section': '每部分题目数',
    'Default: Official SSAT counts': '默认：官方SSAT题目数',
    'Custom: Choose your own counts': '自定义：选择你的题目数',
    'Please select at least one section': '请至少选择一个部分',
    'Question counts must be between 1 and 30': '题目数量必须在1到30之间',
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

  const handleCompleteTestGeneration = () => {
    if (showCustomization) {
      // Validate custom configuration
      if (selectedSections.length === 0) {
        alert(t('Please select at least one section'))
        return
      }
      
      // Check for valid question counts
      const invalidCounts = selectedSections.filter(section => {
        const count = customCounts[section] || 0
        return count < 1 || count > 30
      })
      
      if (invalidCounts.length > 0) {
        alert(t('Question counts must be between 1 and 30'))
        return
      }
      
      // Use custom configuration
      onGenerateCompleteTest({
        sections: selectedSections,
        counts: customCounts,
        difficulty: formData.difficulty
      })
    } else {
      // Use default configuration (preserves existing behavior)
      onGenerateCompleteTest()
    }
  }

  const questionTypes = [
    { value: 'quantitative', label: 'Quantitative' },
    { value: 'reading', label: 'Reading' },
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
          onClick={handleCompleteTestGeneration}
          disabled={loading}
          className="flex-1"
        >
          {loading ? t('Generating...') : t('Generate Complete Test')}
        </Button>
      </div>

      {/* Complete Test Customization Toggle */}
      <div className="border-t pt-6">
        <div className="flex items-center space-x-3 mb-4">
          <input
            type="checkbox"
            id="customize-toggle"
            checked={showCustomization}
            onChange={(e) => setShowCustomization(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <Label htmlFor="customize-toggle" className="text-base font-medium">
            {t('Customize Complete Test')}
          </Label>
        </div>
        
        <p className="text-sm text-gray-600 mb-4">
          {showCustomization ? t('Custom: Choose your own counts') : t('Default: Official SSAT counts')}
        </p>

        {/* Customization Options */}
        {showCustomization && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            {/* Section Selection */}
            <div>
              <Label className="text-sm font-medium mb-3 block">{t('Select Sections')}</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {questionTypes.map(({ value, label }) => (
                  <div key={value} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id={`section-${value}`}
                      checked={selectedSections.includes(value)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedSections(prev => [...prev, value])
                        } else {
                          setSelectedSections(prev => prev.filter(s => s !== value))
                        }
                      }}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <Label htmlFor={`section-${value}`} className="text-sm">
                      {label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Question Counts */}
            <div>
              <Label className="text-sm font-medium mb-3 block">{t('Questions per Section')}</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {selectedSections.map(section => {
                  const sectionLabel = questionTypes.find(qt => qt.value === section)?.label || section
                  return (
                    <div key={section} className="space-y-1">
                      <Label htmlFor={`count-${section}`} className="text-xs text-gray-600">
                        {sectionLabel}
                      </Label>
                      <Input
                        id={`count-${section}`}
                        type="number"
                        min="1"
                        max="30"
                        value={customCounts[section] || 5}
                        onChange={(e) => setCustomCounts(prev => ({
                          ...prev,
                          [section]: parseInt(e.target.value) || 1
                        }))}
                        className="text-sm"
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
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