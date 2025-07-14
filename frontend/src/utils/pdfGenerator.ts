/**
 * Unified PDF Generator for SSAT Questions
 * Handles both individual practice questions and complete tests with professional formatting
 */

import { Question, TestSection, StandaloneSection, ReadingSection, WritingSection } from '@/types/api'

// Normalized question structure for PDF generation
interface PDFQuestion {
  number: number
  text: string
  options?: { letter: string; text: string }[]
  correct_answer?: string
  explanation?: string
  tags?: string[]
  visual_description?: string
  sectionName?: string
  isPassage?: boolean
  passageText?: string
}

// PDF generation options
interface PDFOptions {
  title: string
  includeAnswers: boolean
  showSectionBreaks: boolean
  language: 'en' | 'zh'
  testType: 'individual' | 'complete'
}

// Translation mappings
const translations = {
  'SSAT Practice Questions': 'SSAT 练习题',
  'Complete SSAT Practice Test': '完整SSAT模拟考试',
  'Generated on': '生成于',
  'questions ready for practice': '道题目准备练习',
  'questions': '道题目',
  'With Answer Key': '含答案',
  'Questions Only': '仅题目',
  'Question': '题目',
  'Correct Answer': '正确答案',
  'Answer': '答案',
  'Explanation': '解析',
  'Visual Element': '图像元素',
  'Topics': '主题',
  'Answer Key': '答案',
  'Reading Passage': '阅读材料',
  'Writing Prompt': '写作提示',
  'Section': '部分',
  'Quantitative': '数学',
  'Reading': '阅读',
  'Analogies': '类比',
  'Synonyms': '同义词',
  'Writing': '写作'
}

const t = (key: string, language: 'en' | 'zh') => 
  language === 'zh' ? (translations[key as keyof typeof translations] || key) : key

/**
 * Normalize different question formats into a unified structure
 */
export function normalizeQuestionsForPDF(
  data: Question[] | TestSection[], 
  options: PDFOptions
): PDFQuestion[] {
  const normalized: PDFQuestion[] = []
  let questionCounter = 1

  if (Array.isArray(data) && data.length > 0) {
    // Check if it's a simple Question array (individual questions)
    if ('text' in data[0]) {
      const questions = data as Question[]
      questions.forEach((question) => {
        // Check if this is a passage
        if (question.question_type === 'passage' && question.metadata?.isPassage) {
          // Add passage as a special item
          normalized.push({
            number: questionCounter, // Don't increment for passages
            text: question.text,
            sectionName: t('Reading', options.language),
            isPassage: true,
            passageText: question.text
          })
          return
        }
        
        // Map question_type to readable names
        const sectionName = question.question_type === 'quantitative' ? t('Quantitative', options.language) :
                           question.question_type === 'analogy' ? t('Analogies', options.language) :
                           question.question_type === 'synonym' ? t('Synonyms', options.language) :
                           question.question_type === 'reading' ? t('Reading', options.language) :
                           question.question_type === 'writing' ? t('Writing', options.language) :
                           question.question_type
        
        normalized.push({
          number: questionCounter++,
          text: question.text,
          options: question.options,
          correct_answer: question.correct_answer,
          explanation: question.explanation,
          tags: question.tags,
          visual_description: question.visual_description,
          sectionName: sectionName
        })
      })
    } else {
      // It's TestSection array (complete test)
      const sections = data as TestSection[]
      sections.forEach((section) => {
        if (section.section_type === 'reading') {
          const readingSection = section as ReadingSection
          readingSection.passages.forEach((passage) => {
            // Add passage as a special "question"
            normalized.push({
              number: questionCounter,
              text: passage.text,
              sectionName: t('Reading', options.language),
              isPassage: true,
              passageText: passage.text
            })
            
            // Add questions for this passage
            passage.questions.forEach((question) => {
              normalized.push({
                number: questionCounter++,
                text: question.text,
                options: question.options,
                correct_answer: question.correct_answer,
                explanation: question.explanation,
                tags: question.tags,
                visual_description: question.visual_description,
                sectionName: t('Reading', options.language)
              })
            })
          })
        } else if (section.section_type === 'writing') {
          const writingSection = section as WritingSection
          normalized.push({
            number: questionCounter++,
            text: writingSection.prompt.prompt_text,
            sectionName: t('Writing', options.language),
            visual_description: writingSection.prompt.visual_description
          })
        } else {
          // Standalone sections (quantitative, analogy, synonym)
          const standaloneSection = section as StandaloneSection
          const sectionName = t(section.section_type === 'quantitative' ? 'Quantitative' : 
                               section.section_type === 'analogy' ? 'Analogies' : 'Synonyms', 
                               options.language)
          
          standaloneSection.questions.forEach((question) => {
            normalized.push({
              number: questionCounter++,
              text: question.text,
              options: question.options,
              correct_answer: question.correct_answer,
              explanation: question.explanation,
              tags: question.tags,
              visual_description: question.visual_description,
              sectionName
            })
          })
        }
      })
    }
  }

  return normalized
}

/**
 * Generate professional PDF styling
 */
function generatePDFStyles(): string {
  return `
    body { 
      font-family: Times, "Times New Roman", serif; 
      line-height: 1.5; 
      margin: 30px; 
      font-size: 12pt; 
      color: #000;
    }
    .header { 
      text-align: center; 
      margin-bottom: 25px; 
      border-bottom: 1px solid #333; 
      padding-bottom: 10px; 
    }
    .header h1 { 
      font-size: 18pt; 
      margin: 0 0 8px 0; 
      font-weight: bold; 
    }
    .header p { 
      margin: 4px 0; 
      font-size: 11pt; 
      color: #555; 
    }
    .section-break { 
      page-break-before: always; 
      margin-top: 20px; 
      margin-bottom: 15px; 
      border-top: 2px solid #333; 
      padding-top: 15px; 
    }
    .section-break-first { 
      margin-top: 20px; 
      margin-bottom: 15px; 
      border-top: 2px solid #333; 
      padding-top: 15px; 
    }
    .section-break h2, .section-break-first h2 { 
      font-size: 14pt; 
      margin: 0 0 10px 0; 
      font-weight: bold; 
    }
    .question { 
      margin-bottom: 15px; 
      page-break-inside: avoid; 
    }
    .question-text { 
      margin-bottom: 6px; 
      line-height: 1.3; 
    }
    .question-number-inline { 
      font-weight: bold; 
      margin-right: 6px; 
    }
    .options { 
      margin: 6px 0 0 0; 
    }
    .option { 
      margin: 2px 0; 
      padding: 0; 
      background: none; 
      line-height: 1.3; 
    }
    .option.correct-answer { 
      background: #e8f5e8; 
      font-weight: bold; 
      padding: 2px 4px; 
      border-radius: 3px; 
    }
    .answer-section { 
      margin-top: 12px; 
      padding: 10px; 
      background: #f5f5f5; 
      border-radius: 4px; 
      border-left: 3px solid #666; 
      font-size: 11pt; 
    }
    .tags { 
      margin-top: 8px; 
    }
    .tag { 
      background: #e5e5e5; 
      color: #333; 
      padding: 2px 6px; 
      border-radius: 3px; 
      font-size: 10pt; 
      margin-right: 6px; 
    }
    .visual-desc { 
      background: #f0f8ff; 
      padding: 8px; 
      border-radius: 4px; 
      margin: 8px 0; 
      border-left: 3px solid #666; 
      font-style: italic; 
      font-size: 11pt; 
    }
    .passage { 
      background: #f8f9fa; 
      padding: 15px; 
      border-radius: 4px; 
      margin: 15px 0; 
      border-left: 4px solid #007bff; 
      font-size: 11pt; 
      line-height: 1.6; 
    }
    .answer-key { 
      page-break-before: always; 
      margin-top: 30px; 
    }
    .answer-key h2 { 
      font-size: 14pt; 
      margin-bottom: 15px; 
      border-bottom: 1px solid #333; 
      padding-bottom: 5px; 
    }
    .answer-grid { 
      display: grid; 
      grid-template-columns: repeat(5, 1fr); 
      gap: 8px; 
    }
    .answer-item { 
      text-align: center; 
      padding: 6px; 
      background: #f3f4f6; 
      border-radius: 3px; 
      font-size: 11pt; 
    }
    @media print { 
      body { margin: 20px; font-size: 11pt; } 
      .question { page-break-inside: avoid; margin-bottom: 12px; }
      .question-text { margin-bottom: 4px; }
      .options { margin: 4px 0 0 0; }
      .option { margin: 1px 0; }
      .section-break { page-break-before: always; }
      .section-break-first { page-break-before: avoid; }
    }
  `
}

/**
 * Generate the main PDF content
 */
function generatePDFContent(questions: PDFQuestion[], options: PDFOptions): string {
  // Get question types for individual questions
  const questionTypes = new Set<string>()
  questions.forEach(q => {
    if (!q.isPassage && q.sectionName) {
      questionTypes.add(q.sectionName)
    }
  })
  
  // Build header info
  const questionCount = questions.filter(q => !q.isPassage).length
  const questionTypeText = questionTypes.size > 0 ? Array.from(questionTypes).join(', ') : ''
  
  let headerInfo = `${questionCount} ${t('questions', options.language)}`
  if (questionTypeText && options.testType === 'individual') {
    headerInfo += ` • ${questionTypeText}`
  }
  
  let content = `
    <div class="header">
      <h1>${t(options.title, options.language)}</h1>
      <p>${t('Generated on', options.language)} ${new Date().toLocaleDateString()}</p>
      <p>${headerInfo}</p>
    </div>
  `

  let currentSection = ''
  let isFirstSection = true
  
  questions.forEach((question) => {
    // Add section break if needed
    if (options.showSectionBreaks && question.sectionName && question.sectionName !== currentSection) {
      currentSection = question.sectionName
      // Use different class for first section (no page break) vs subsequent sections
      const sectionClass = isFirstSection ? 'section-break-first' : 'section-break'
      content += `
        <div class="${sectionClass}">
          <h2>${question.sectionName} ${t('Section', options.language)}</h2>
        </div>
      `
      isFirstSection = false
    }

    // Handle reading passages
    if (question.isPassage && question.passageText) {
      content += `
        <div class="passage">
          <strong>${t('Reading Passage', options.language)}:</strong><br>
          ${question.passageText}
        </div>
      `
      return
    }

    // Regular questions
    content += `
      <div class="question">
        <p class="question-text"><span class="question-number-inline">${question.number}.</span>${question.text}</p>
        
        ${question.visual_description ? `
          <div class="visual-desc">
            <strong>${t('Visual Element', options.language)}:</strong> ${question.visual_description}
          </div>
        ` : ''}
        
        ${question.options && question.options.length > 0 ? `
          <div class="options">
            ${question.options.map(option => `
              <div class="option ${options.includeAnswers && option.letter === question.correct_answer ? 'correct-answer' : ''}">
                ${option.letter}) ${option.text}
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${options.includeAnswers && question.correct_answer ? `
          <div class="answer-section">
            <div><strong>${t('Correct Answer', options.language)}:</strong> ${question.correct_answer}</div>
            ${question.explanation ? `<div><strong>${t('Explanation', options.language)}:</strong> ${question.explanation}</div>` : ''}
            ${question.tags && question.tags.length > 0 ? `
              <div class="tags">
                <strong>${t('Topics', options.language)}:</strong> 
                ${question.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        ` : ''}
      </div>
    `
  })

  // Add answer key if answers are not shown
  if (!options.includeAnswers) {
    const questionsWithAnswers = questions.filter(q => !q.isPassage && q.correct_answer)
    if (questionsWithAnswers.length > 0) {
      content += `
        <div class="answer-key">
          <h2>${t('Answer Key', options.language)}</h2>
          <div class="answer-grid">
            ${questionsWithAnswers.map((question) => `
              <div class="answer-item">
                <strong>${question.number}.</strong> ${question.correct_answer}
              </div>
            `).join('')}
          </div>
        </div>
      `
    }
  }

  return content
}

/**
 * Main unified PDF generation function
 */
export function generateUnifiedPDF(
  data: Question[] | TestSection[],
  options: PDFOptions
): void {
  const questions = normalizeQuestionsForPDF(data, options)
  const styles = generatePDFStyles()
  const content = generatePDFContent(questions, options)

  const printWindow = window.open('', '_blank')
  if (!printWindow) return

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <title>${options.title} - ${new Date().toISOString().split('T')[0]}</title>
        <style>${styles}</style>
      </head>
      <body>
        ${content}
      </body>
    </html>
  `

  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  
  setTimeout(() => {
    printWindow.print()
    printWindow.close()
  }, 250)
}