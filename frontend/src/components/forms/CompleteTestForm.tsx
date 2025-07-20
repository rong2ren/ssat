'use client'

import { useState } from 'react'
import { Button } from '../ui/Button'
import { Select } from '../ui/Select'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'

interface CompleteTestFormProps {
  onSubmit: (customConfig?: {
    sections: string[]
    counts: Record<string, number>
    difficulty: string
  }) => void
  loading: boolean
  showChinese?: boolean
}

export function CompleteTestForm({ onSubmit, loading, showChinese = false }: CompleteTestFormProps) {
  const [difficulty, setDifficulty] = useState('Medium')
  const [useCustomization, setUseCustomization] = useState(false)
  const [showOfficialDetails, setShowOfficialDetails] = useState(false)
  const [selectedSections, setSelectedSections] = useState(['quantitative', 'analogy', 'synonym', 'reading', 'writing'])
  const [customCounts, setCustomCounts] = useState<Record<string, number>>({
    quantitative: 1,
    reading: 1,
    analogy: 1,
    synonym: 1,
    writing: 1
  })

  // UI translations
  const translations = {
    'Overall Difficulty': '整体难度',
    'Generate Complete Test': '生成完整测试',
    'Configure Test': '配置测试',
    'Generating...': '生成中...',
    'Test Format': '测试格式',
    'Use Official SSAT Format': '使用官方SSAT格式',
    'Customize Sections': '自定义',
    'Select Test Sections': '选择题型',
    'Questions per Section': '每部分题目数',
    'Official test format with standard question counts (89 total)': '官方测试格式，标准题目数量（共89题）',
    'Pick sections and question counts': '自由选择题型和数量',
    'Applied to all sections in the test': '应用于测试的所有部分',
    'Recommended': '推荐',
    'Questions:': '题目数：',
    'Quantitative': '数学',
    'Verbal': '语言',
    'Reading': '阅读',
    'Analogies': '类比',
    'Synonyms': '同义词',
    'Writing': '写作',
    'Math problems and numerical reasoning': '数学问题和数值推理',
    'Reading comprehension passages': '阅读理解文章',
    'Word relationship patterns': '词汇关系模式',
    'Word meaning identification': '词义识别',
    'Creative writing prompt': '作文',
    'Easy': '简单',
    'Medium': '中等',
    'Hard': '困难',
    'Total': '总计',
    'Please select at least one section': '请至少选择一个部分',
    'Question counts must be between 1 and 15 for custom generation': '自定义生成题目数量必须在1到15之间',
    'Math Breakdown': '数学细分',
    'Number Operations': '数字运算',
    'Algebra Functions': '代数函数',
    'Geometry Spatial': '几何空间',
    'Measurement': '测量',
    'Probability Data': '概率数据',
    'addition, subtraction, fractions': '加法、减法、分数',
    'patterns, sequences, equations': '模式、序列、方程',
    'shapes, area, spatial reasoning': '形状、面积、空间推理',
    'length, time, units': '长度、时间、单位',
    'graphs, data analysis': '图表、数据分析',
    'Verbal Breakdown': '语言细分',
    'word meaning, definitions': '词义、定义',
    'word relationships, patterns': '词汇关系、模式',
    'Note: Custom tests do not include topic breakdowns for quantitative': '注意：自定义测试不包含数学部分的主题细分'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (useCustomization) {
      // Validate custom configuration
      if (selectedSections.length === 0) {
        alert(t('Please select at least one section'))
        return
      }
      
      const invalidCounts = selectedSections.filter(section => {
        const count = customCounts[section] || 0
        return count < 1 || count > 15
      })
      
      if (invalidCounts.length > 0) {
        alert(t('Question counts must be between 1 and 15 for custom generation'))
        return
      }
      
      onSubmit({
        sections: selectedSections,
        counts: customCounts,
        difficulty: difficulty
      })
    } else {
      // Use official SSAT Elementary format
      onSubmit()
    }
  }

  const difficulties = [
    { value: 'Easy', label: t('Easy') },
    { value: 'Medium', label: t('Medium') },
    { value: 'Hard', label: t('Hard') }
  ]

  const sectionTypes = [
    { value: 'quantitative', label: t('Quantitative'), defaultCount: 1 },
    { value: 'analogy', label: t('Analogies'), defaultCount: 1 },
    { value: 'synonym', label: t('Synonyms'), defaultCount: 1 },
    { value: 'reading', label: t('Reading'), defaultCount: 1 },
    { value: 'writing', label: t('Writing'), defaultCount: 1 }
  ]

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {t('Generate Complete Test')}
        </h2>
        <p className="text-gray-600">
          Create a comprehensive SSAT practice test with multiple sections
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Overall Difficulty */}
        <div className="space-y-2">
          <Label htmlFor="test-difficulty">{t('Overall Difficulty')} *</Label>
          <Select
            value={difficulty}
            onChange={setDifficulty}
            options={difficulties}
            id="test-difficulty"
            className="md:w-1/3"
          />
          <p className="text-xs text-gray-500">{t('Applied to all sections in the test')}</p>
        </div>

        {/* Enhanced Format Selection */}
        <div className="space-y-4">
          <Label className="text-base font-medium">{t('Test Format')}</Label>
          
          <div className="grid md:grid-cols-2 gap-4">
            {/* Official Format Card */}
            <div className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              !useCustomization 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setUseCustomization(false)}
            >
              <div className="flex items-center justify-between mb-3">
                <Label className="font-medium text-lg cursor-pointer">
                  {t('Use Official SSAT Format')}
                </Label>
                <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                  {t('Recommended')}
                </span>
              </div>
              
              <p className="text-sm text-gray-600 mb-3">
                ✓ {t('Official test format with standard question counts (89 total)')}
              </p>
              
              <div className="text-xs text-gray-500 mb-2">
                {t('Quantitative')} (30) • {t('Verbal')} (30) • {t('Reading')} (28) • {t('Writing')} (1)
              </div>
              
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowOfficialDetails(!showOfficialDetails)
                }}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                {showOfficialDetails ? 'Hide Math & Verbal Breakdown ▼' : 'Show Math & Verbal Breakdown ▼'}
              </button>
              
              {showOfficialDetails && (
                <div className="text-xs text-gray-600 space-y-1 mt-2">
                  <div className="font-medium">{t('Math Breakdown')}:</div>
                  <div className="ml-2">
                    • {t('Number Operations')} (12) - {t('addition, subtraction, fractions')}<br/>
                    • {t('Algebra Functions')} (6) - {t('patterns, sequences, equations')}<br/>
                    • {t('Geometry Spatial')} (8) - {t('shapes, area, spatial reasoning')}<br/>
                    • {t('Measurement')} (3) - {t('length, time, units')}<br/>
                    • {t('Probability Data')} (1) - {t('graphs, data analysis')}
                  </div>
                  <div className="font-medium mt-2">{t('Verbal Breakdown')}:</div>
                  <div className="ml-2">
                    • {t('Synonyms')} (18) - {t('word meaning, definitions')}<br/>
                    • {t('Analogies')} (12) - {t('word relationships, patterns')}
                  </div>
                </div>
              )}
            </div>

            {/* Custom Format Card */}
            <div className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              useCustomization 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setUseCustomization(true)}
            >
              <Label className="font-medium text-lg cursor-pointer block mb-3">
                {t('Customize Sections')}
              </Label>
              
              <p className="text-sm text-gray-600 mb-2">
                ⚙️ {t('Pick sections and question counts')}
              </p>
              
              <p className="text-xs text-gray-500">
                {t('Note: Custom tests do not include topic breakdowns for quantitative')}
              </p>
            </div>
          </div>
        </div>

        {/* Customization Options */}
        {useCustomization && (
          <div className="bg-gray-50 rounded-lg p-6 space-y-6">
            {/* Combined Section Selection and Counts */}
            <div>
              <Label className="text-sm font-medium mb-3 block">{t('Select Test Sections')}</Label>
              <div className="space-y-1">
                {sectionTypes.map((section) => (
                  <div key={section.value} className={`flex items-center space-x-4 py-1 px-2 border rounded-lg ${
                    !selectedSections.includes(section.value) ? 'opacity-50 bg-gray-50' : ''
                  }`}>
                    <input
                      type="checkbox"
                      id={`section-${section.value}`}
                      checked={selectedSections.includes(section.value)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedSections(prev => [...prev, section.value])
                        } else {
                          setSelectedSections(prev => prev.filter(s => s !== section.value))
                        }
                      }}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    
                    <div className="flex-1">
                      <Label htmlFor={`section-${section.value}`} className={`font-medium cursor-pointer ${
                        !selectedSections.includes(section.value) ? 'text-gray-500' : ''
                      }`}>
                        {t(section.label)}
                      </Label>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Label className="text-sm text-gray-600 whitespace-nowrap">{t('Questions:')}</Label>
                      <Input
                        type="number"
                        min="1"
                        max="15"
                        value={customCounts[section.value] || section.defaultCount}
                        onChange={(e) => setCustomCounts(prev => ({
                          ...prev,
                          [section.value]: parseInt(e.target.value) || 1
                        }))}
                        disabled={!selectedSections.includes(section.value)}
                        className={`w-16 text-sm ${
                          !selectedSections.includes(section.value) ? 'bg-gray-100 text-gray-400' : ''
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-center pt-4">
          <Button 
            type="submit" 
            disabled={loading}
            className="w-full md:w-auto min-w-48"
            size="lg"
          >
            {loading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                {t('Generating...')}
              </div>
            ) : (
              t('Generate Complete Test')
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}