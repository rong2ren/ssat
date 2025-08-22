export interface QuestionOption {
  letter: string
  text: string
}

export interface Question {
  id?: string
  question_type: string
  difficulty: string
  text: string
  options: QuestionOption[]
  correct_answer: string
  explanation: string
  cognitive_level: string
  tags: string[]
  visual_description?: string
  image_path?: string
  metadata?: Record<string, any>
}

export interface QuestionRequest {
  question_type: 'quantitative' | 'reading' | 'analogy' | 'synonym' | 'writing'
  difficulty: 'Easy' | 'Medium' | 'Hard'
  topic?: string
  count: number
}

export interface CompleteTestRequest {
  difficulty: 'Easy' | 'Medium' | 'Hard'
  include_sections: ('quantitative' | 'reading' | 'analogy' | 'synonym' | 'writing')[]
  custom_counts?: Record<string, number>
}

export interface GenerationMetadata {
  generation_time: number
  provider_used: string
  training_examples_count: number
  request_id?: string
  timestamp: string
}

export interface QuestionGenerationResponse {
  questions: Question[]
  metadata: GenerationMetadata
  status: string
  count: number
}

export interface ReadingPassage {
  id: string
  title?: string
  text: string
  passage_type: 'fiction' | 'non_fiction' | 'poetry' | 'biography'
  grade_level: string
  topic: string
  questions: Question[]
  metadata: Record<string, any>
}

export interface WritingPrompt {
  prompt_text: string
  instructions: string
  visual_description?: string
  image_path?: string
  grade_level: string
  prompt_type: string
}

export interface StandaloneSection {
  section_type: 'quantitative' | 'analogy' | 'synonym'
  questions: Question[]
  instructions: string
}

export interface ReadingSection {
  section_type: 'reading'
  passages: ReadingPassage[]
  instructions: string
}

export interface WritingSection {
  section_type: 'writing'
  prompt: WritingPrompt
  instructions: string
}

export type TestSection = StandaloneSection | ReadingSection | WritingSection

export interface CompleteTestResponse {
  test_id?: string
  sections: TestSection[]
  metadata: GenerationMetadata
  status: string
  total_questions: number
  estimated_time_minutes: number
  test_info?: Record<string, any>
}

// ========================================
// AUTHENTICATION TYPES
// ========================================

export type GradeLevel = '3rd' | '4th' | '5th' | '6th' | '7th' | '8th'

export interface UserProfile {
  id: string
  email: string
  full_name?: string
  grade_level?: GradeLevel
  role?: string
  created_at: string
  updated_at: string
  deleted_at?: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface ResetPasswordRequest {
  email: string
}



export interface UserRegister {
  email: string
  password: string
  full_name?: string
  grade_level?: GradeLevel
}

export interface UserProfileUpdate {
  full_name?: string
  grade_level?: GradeLevel
}

export interface UserContentStats {
  quantitative_count: number
  analogy_count: number
  synonym_count: number
  reading_count: number
  writing_count: number
}

export interface AuthResponse {
  success: boolean
  message: string
  user?: UserProfile
  token?: string
}

export interface UserProfileResponse {
  success: boolean
  message: string
  profile?: UserProfile
}

export interface UserStatsResponse {
  success: boolean
  message: string
  stats?: UserContentStats
}