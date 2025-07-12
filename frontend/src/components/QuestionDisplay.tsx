'use client'

import { useState } from 'react'
import { Button } from './ui/Button'
import { Question } from '@/types/api'
import { Download, Printer, Eye, EyeOff } from 'lucide-react'

interface QuestionDisplayProps {
  questions: Question[]
  showChinese: boolean
}

export function QuestionDisplay({ questions, showChinese }: QuestionDisplayProps) {
  const [showAnswers, setShowAnswers] = useState(false)

  // UI translations mapping
  const translations = {
    // Header
    'Generated Questions': '生成的题目',
    'questions ready for practice': '道题目准备练习',
    'Show Answers': '显示答案',
    'Hide Answers': '隐藏答案', 
    'Save as PDF': '保存为PDF',
    'Print': '打印',
    
    // Question content
    'Question': '题目',
    'Correct Answer': '正确答案',
    'Explanation': '解析',
    'Visual Element': '图像元素',
    'Topics': '主题',
    'Answer Key': '答案',
    
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  const handlePrint = () => {
    window.print()
  }

  const handleDownload = () => {
    // Use browser's print dialog with "Save as PDF" option
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    
    const printContent = generatePrintableHTML(questions, showAnswers, showChinese)
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>SSAT Practice Questions - ${new Date().toISOString().split('T')[0]}</title>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
            .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 15px; }
            .question { margin-bottom: 30px; page-break-inside: avoid; }
            .question-number { font-weight: bold; color: #2563eb; }
            .options { margin: 15px 0; }
            .option { margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; }
            .answer-section { margin-top: 15px; padding: 15px; background: #dcfce7; border-radius: 6px; border-left: 4px solid #16a34a; }
            .tags { margin-top: 10px; }
            .tag { background: #e0e7ff; color: #3730a3; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }
            .visual-desc { background: #dbeafe; padding: 12px; border-radius: 4px; margin: 10px 0; border-left: 4px solid #2563eb; }
            @media print { 
              body { margin: 20px; } 
              .question { page-break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          ${printContent}
        </body>
      </html>
    `)
    
    printWindow.document.close()
    
    // Auto-focus and print
    printWindow.focus()
    setTimeout(() => {
      printWindow.print()
      printWindow.close()
    }, 250)
  }

  const generatePrintableHTML = (questions: Question[], includeAnswers: boolean, isChinese: boolean = false) => {
    const pdfT = (key: string) => isChinese ? (translations[key as keyof typeof translations] || key) : key
    
    let content = `
      <div class="header">
        <h1>SSAT Practice Questions</h1>
        <p>Generated on ${new Date().toLocaleDateString()}</p>
        <p>${questions.length} ${pdfT('questions ready for practice')} • ${includeAnswers ? pdfT('Show Answers') : pdfT('Answer Key')}</p>
      </div>
    `
    
    questions.forEach((question, index) => {
      content += `
        <div class="question">
          <div class="question-number">${pdfT('Question')} ${index + 1}</div>
          <p><strong>${question.text}</strong></p>
          
          ${question.visual_description ? `
            <div class="visual-desc">
              <strong>${pdfT('Visual Element')}:</strong> ${question.visual_description}
            </div>
          ` : ''}
          
          <div class="options">
            ${question.options.map(option => `
              <div class="option ${includeAnswers && option.letter === question.correct_answer ? 'style="background: #dcfce7; border-left: 4px solid #16a34a;"' : ''}">
                <strong>${option.letter})</strong> ${option.text}
              </div>
            `).join('')}
          </div>
          
          ${includeAnswers ? `
            <div class="answer-section">
              <div><strong>${pdfT('Correct Answer')}:</strong> ${question.correct_answer}</div>
              <div><strong>${pdfT('Explanation')}:</strong> ${question.explanation}</div>
              ${question.tags && question.tags.length > 0 ? `
                <div class="tags">
                  <strong>${pdfT('Topics')}:</strong> 
                  ${question.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          ` : ''}
        </div>
      `
    })
    
    if (!includeAnswers) {
      content += `
        <div style="page-break-before: always; margin-top: 40px;">
          <h2>${pdfT('Answer Key')}</h2>
          <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;">
            ${questions.map((question, index) => `
              <div style="text-align: center; padding: 8px; background: #f3f4f6; border-radius: 4px;">
                <strong>${index + 1}.</strong> ${question.correct_answer}
              </div>
            `).join('')}
          </div>
        </div>
      `
    }
    
    return content
  }

  if (questions.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-gray-800">{t('Generated Questions')}</h2>
            <p className="text-gray-600">{questions.length} {t('questions ready for practice')}</p>
          </div>
          
          <div className="flex space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAnswers(!showAnswers)}
              className="flex items-center space-x-2"
            >
              {showAnswers ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              <span>{showAnswers ? t('Hide Answers') : t('Show Answers')}</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>{t('Save as PDF')}</span>
            </Button>
            
            <Button
              size="sm"
              onClick={handlePrint}
              className="flex items-center space-x-2"
            >
              <Printer className="h-4 w-4" />
              <span>{t('Print')}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Questions List */}
      <div className="p-6 space-y-8 print:p-4">
        {questions.map((question, index) => (
          <div key={index} className="border-b border-gray-100 last:border-b-0 pb-8 last:pb-0">
            {/* Question Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded">
                    {t('Question')} {index + 1}
                  </span>
                  <span className="bg-gray-100 text-gray-800 text-sm font-medium px-2.5 py-0.5 rounded capitalize">
                    {question.question_type}
                  </span>
                  <span className="bg-yellow-100 text-yellow-800 text-sm font-medium px-2.5 py-0.5 rounded">
                    {question.difficulty}
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
        ))}
      </div>

      {/* Print-only Answer Key */}
      {!showAnswers && (
        <div className="hidden print:block p-6 border-t border-gray-200">
          <h3 className="text-xl font-semibold mb-4">{t('Answer Key')}</h3>
          <div className="grid grid-cols-5 gap-4">
            {questions.map((question, index) => (
              <div key={index} className="text-center">
                <span className="font-medium">{index + 1}. </span>
                <span className="font-bold">{question.correct_answer}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}