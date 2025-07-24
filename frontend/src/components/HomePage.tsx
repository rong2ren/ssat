'use client'

import { Button } from './ui/Button'
import { BookOpen, FileText, Target, Zap, Clock, Award, ArrowRight } from 'lucide-react'
import Link from 'next/link'

interface HomePageProps {
  showChinese?: boolean
}

export function HomePage({ showChinese = false }: HomePageProps) {
  // console.log('🔄 HomePage: Component rendering')
  
  // UI translations
  const translations = {
    'Master the': '高效掌握',
    'SSAT': 'SSAT考试',
    'with': '，借助',
    'AI-Generated Practice': 'AI智能练习',
    'Get unlimited, personalized SSAT practice questions powered by advanced AI. Practice by section or take full-length tests — all with instant, detailed explanations.': 
      '利用先进AI技术生成海量个性化SSAT练习题。支持单项自定义练习或完整模拟测试，并提供即时详解，助您精准提升。',
  
    'Start Custom Practice': '开始单项自定义练习',
    'Take Full Practice Test': '开始完整模拟测试',
  
    'Why Choose Our SSAT Practice Platform?': '为什么选择我们的SSAT智能练习平台？',
    'Our AI-driven platform delivers a personalized, realistic SSAT prep experience — complete with targeted practice and instant feedback.':
      '我们的平台依托先进的AI技术，提供全面且针对性的 SSAT 练习题，助您高效备考。',
  
    'AI-Generated Questions': 'AI智能生成题目',
    'Get unlimited, unique practice questions that match the exact format and difficulty of the real SSAT exam.':
      '生成海量题目，精准匹配SSAT考试的题型和难度。',
  
    'Targeted Practice': '专项强化训练',
    'Focus on specific topics within Math, Verbal, Reading, and Writing sections to strengthen weak areas.':
      '聚焦数学、词汇、阅读和写作各部分的重点与薄弱环节，实现有针对性的提升。',
  
    'Instant Feedback': '即时解析与反馈',
    'Get detailed explanations for every question to understand concepts and improve your performance.':
      '每道题均配有详细解析，帮助深入理解知识点，提升答题技巧。',
  
    'Choose Your Practice Mode': '选择您的练习模式',
    'Flexible options to match your study schedule and goals.': '灵活配置，满足不同学习需求与时间安排。',
  
    'Custom Section Practice': '单项自定义练习',
    'Targeted Learning': '专项学习',
  
    'Choose any section (Math, Verbal, Reading, Writing)': '可选择任意科目（数学、词汇、阅读、写作）',
    'Select difficulty level and number of questions': '选择题目难度和数量',
    'Focus on specific topics within sections': '可聚焦具体知识点进行强化',
    'Perfect for quick practice sessions': '适合日常短时间练习',
  
    'Full Practice Test': '完整模拟测试',
    'Complete Assessment': '全面评估',
  
    'Standard SSAT format with multiple sections': '按照SSAT标准格式，涵盖所有考试部分',
    'Customizable section configuration': '支持灵活定制考试科目组合',
    'Comprehensive answer key with explanations': '提供全套答案与详尽解析',
    'PDF export for offline practice': '支持PDF导出，便于线下练习',
  
    'SSAT Test Sections': 'SSAT考试科目一览',
    'Comprehensive coverage of all SSAT sections with authentic question types.':
      '全面覆盖SSAT各科目，题型真实，贴合考试要求。',
  
    'Math': '数学',
    'Arithmetic, algebra, geometry, and data analysis': '包括算术、代数、几何和数据分析等内容',
  
    'Verbal': '词汇',
    'Synonyms, analogies, and vocabulary': '涵盖同义词、类比推理及词汇理解',
  
    'Reading': '阅读',
    'Reading comprehension passages and questions': '阅读理解文章及相关题目',
  
    'Writing': '写作',
    'Grammar, usage, and writing mechanics': '涉及语法、句式和写作技巧',
  
    // Topics
    'Fractions': '分数',
    'Algebra': '代数',
    'Geometry': '几何',
    'Word Problems': '应用题',
    'Synonyms': '同义词',
    'Analogies': '类比',
    'Vocabulary': '词汇',
    'Word Relationships': '词汇关系',
    'Literature': '文学',
    'Science': '科学',
    'History': '历史',
    'Critical Reading': '批判性阅读',
    'Grammar': '语法',
    'Punctuation': '标点',
    'Sentence Structure': '句子结构',
    'Style': '写作风格'
  }

  const t = (key: string) => showChinese ? (translations[key as keyof typeof translations] || key) : key

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              {t('Master the')} <span className="text-blue-600">{t('SSAT')}</span> {t('with')}
              <br />
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                {t('AI-Generated Practice')}
              </span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
              {t('Get unlimited, personalized SSAT practice questions powered by advanced AI. Practice by section or take full-length tests — all with instant, detailed explanations.')}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/custom-section">
                <Button size="lg" className="inline-flex items-center px-8 py-4 text-lg shadow-lg hover:shadow-xl">
                  <Target className="mr-2 h-5 w-5" />
                  {t('Start Custom Practice')}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/full-test">
                <Button 
                  variant="outline" 
                  size="lg" 
                  className="inline-flex items-center px-8 py-4 text-lg bg-white/80 backdrop-blur-sm border-2 border-blue-600 text-blue-600 hover:bg-blue-50"
                >
                  <BookOpen className="mr-2 h-5 w-5" />
                  {t('Take Full Practice Test')}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              {t('Why Choose Our SSAT Practice Platform?')}
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              {t('Our AI-driven platform delivers a personalized, realistic SSAT prep experience — complete with targeted practice and instant feedback.')}
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100">
              <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Zap className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">{t('AI-Generated Questions')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('Get unlimited, unique practice questions that match the exact format and difficulty of the real SSAT exam.')}
              </p>
            </div>
            
            <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-green-50 to-emerald-50 border border-green-100">
              <div className="bg-green-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Target className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">{t('Targeted Practice')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('Focus on specific topics within Math, Verbal, Reading, and Writing sections to strengthen weak areas.')}
              </p>
            </div>
            
            <div className="text-center p-8 rounded-2xl bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-100">
              <div className="bg-purple-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Award className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">{t('Instant Feedback')}</h3>
              <p className="text-gray-600 leading-relaxed">
                {t('Get detailed explanations for every question to understand concepts and improve your performance.')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Test Modes Section */}
      <section className="py-20 bg-gray-50/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">{t('Choose Your Practice Mode')}</h2>
            <p className="text-lg text-gray-600">
              {t('Flexible options to match your study schedule and goals.')}
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <Link href="/custom-section" className="group">
              <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200 border border-gray-200 group-hover:border-blue-300 group-hover:scale-105">
                <div className="flex items-center mb-6">
                  <div className="bg-blue-100 p-3 rounded-xl mr-4">
                    <Target className="h-8 w-8 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-semibold text-gray-900">{t('Custom Section Practice')}</h3>
                    <p className="text-blue-600 font-medium">{t('Targeted Learning')}</p>
                  </div>
                </div>
                <ul className="space-y-3 text-gray-600">
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Choose any section (Math, Verbal, Reading, Writing)')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Select difficulty level and number of questions')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Focus on specific topics within sections')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Perfect for quick practice sessions')}</span>
                  </li>
                </ul>
              </div>
            </Link>
            
            <Link href="/full-test" className="group">
              <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200 border border-gray-200 group-hover:border-blue-300 group-hover:scale-105">
                <div className="flex items-center mb-6">
                  <div className="bg-indigo-100 p-3 rounded-xl mr-4">
                    <BookOpen className="h-8 w-8 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-semibold text-gray-900">{t('Full Practice Test')}</h3>
                    <p className="text-indigo-600 font-medium">{t('Complete Assessment')}</p>
                  </div>
                </div>
                <ul className="space-y-3 text-gray-600">
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Standard SSAT format with multiple sections')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Customizable section configuration')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('Comprehensive answer key with explanations')}</span>
                  </li>
                  <li className="flex items-center">
                    <Clock className="h-4 w-4 text-green-500 mr-3" />
                    <span>{t('PDF export for offline practice')}</span>
                  </li>
                </ul>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* SSAT Sections Info */}
      <section className="py-20 bg-white/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">{t('SSAT Test Sections')}</h2>
            <p className="text-lg text-gray-600">
              {t('Comprehensive coverage of all SSAT sections with authentic question types.')}
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: t('Math'),
                description: t('Arithmetic, algebra, geometry, and data analysis'),
                topics: [t('Fractions'), t('Algebra'), t('Geometry'), t('Word Problems')],
                color: 'blue',
                bgColor: 'bg-blue-100',
                textColor: 'text-blue-600'
              },
              {
                title: t('Verbal'),
                description: t('Synonyms, analogies, and vocabulary'),
                topics: [t('Synonyms'), t('Analogies'), t('Vocabulary'), t('Word Relationships')],
                color: 'green',
                bgColor: 'bg-green-100',
                textColor: 'text-green-600'
              },
              {
                title: t('Reading'),
                description: t('Reading comprehension passages and questions'),
                topics: [t('Literature'), t('Science'), t('History'), t('Critical Reading')],
                color: 'purple',
                bgColor: 'bg-purple-100',
                textColor: 'text-purple-600'
              },
              {
                title: t('Writing'),
                description: t('Grammar, usage, and writing mechanics'),
                topics: [t('Grammar'), t('Punctuation'), t('Sentence Structure'), t('Style')],
                color: 'orange',
                bgColor: 'bg-orange-100',
                textColor: 'text-orange-600'
              }
            ].map((section, index) => (
              <div key={index} className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                <div className={`w-16 h-16 ${section.bgColor} rounded-lg flex items-center justify-center mb-4`}>
                  <span className={`${section.textColor} font-bold text-sm`}>
                    {section.title}
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-4">{section.description}</p>
                <div className="space-y-1">
                  {section.topics.map((topic, topicIndex) => (
                    <span key={topicIndex} className="inline-block bg-gray-100 px-2 py-1 rounded text-xs text-gray-600 mr-1 mb-1">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}