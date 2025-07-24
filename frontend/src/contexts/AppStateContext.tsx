'use client'

import React, { createContext, useContext, useReducer, ReactNode } from 'react'
import { Question, ReadingPassage, QuestionRequest, TestSection } from '@/types/api'

// Define the exact state structure matching our current implementation
export interface CustomSectionState {
  questions: Question[]
  passages: ReadingPassage[]
  contentType: 'questions' | 'passages' | 'prompts'
  loading: boolean
  error: string | null
  lastRequest?: QuestionRequest
}

export interface FullTestState {
  testRequest: {
    difficulty: string
    include_sections: string[]
    custom_counts: Record<string, number>
    originalSelection?: string[]
    is_official_format?: boolean
  } | null
  jobStatus: any | null  // Persist jobStatus across tab switches
  completedSections: TestSection[]
  showCompleteTest: boolean
  loading: boolean
  error: string | null
}

export interface UserPreferences {
  showChinese: boolean
}

export interface AppState {
  customSection: CustomSectionState
  fullTest: FullTestState
  preferences: UserPreferences
}

// Action types for state updates
export type AppAction =
  // Custom Section Actions
  | { type: 'CUSTOM_SECTION_SET_LOADING'; payload: boolean }
  | { type: 'CUSTOM_SECTION_SET_ERROR'; payload: string | null }
  | { type: 'CUSTOM_SECTION_SET_QUESTIONS'; payload: { questions: Question[]; contentType: 'questions' | 'prompts'; request?: QuestionRequest } }
  | { type: 'CUSTOM_SECTION_SET_PASSAGES'; payload: { passages: ReadingPassage[]; request?: QuestionRequest } }
  | { type: 'CUSTOM_SECTION_CLEAR' }
  
  // Full Test Actions
  | { type: 'FULL_TEST_SET_REQUEST'; payload: FullTestState['testRequest'] }
  | { type: 'FULL_TEST_SET_SHOW_COMPLETE'; payload: boolean }
  | { type: 'FULL_TEST_SET_JOB_STATUS'; payload: any | null }
  | { type: 'FULL_TEST_ADD_COMPLETED_SECTION'; payload: TestSection }
  | { type: 'FULL_TEST_SET_LOADING'; payload: boolean }
  | { type: 'FULL_TEST_SET_ERROR'; payload: string | null }
  | { type: 'FULL_TEST_CLEAR' }
  
  // Preferences Actions
  | { type: 'SET_SHOW_CHINESE'; payload: boolean }

// Initial state
const initialState: AppState = {
  customSection: {
    questions: [],
    passages: [],
    contentType: 'questions',
    loading: false,
    error: null,
    lastRequest: undefined
  },
  fullTest: {
    testRequest: null,
    jobStatus: null,
    completedSections: [],
    showCompleteTest: false,
    loading: false,
    error: null
  },
  preferences: {
    showChinese: false
  }
}

// Reducer function
function appStateReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    // Custom Section Actions
    case 'CUSTOM_SECTION_SET_LOADING':
      return {
        ...state,
        customSection: {
          ...state.customSection,
          loading: action.payload
        }
      }
      
    case 'CUSTOM_SECTION_SET_ERROR':
      return {
        ...state,
        customSection: {
          ...state.customSection,
          error: action.payload
        }
      }
      
    case 'CUSTOM_SECTION_SET_QUESTIONS':
      return {
        ...state,
        customSection: {
          ...state.customSection,
          questions: action.payload.questions,
          passages: [], // Clear passages when setting questions
          contentType: action.payload.contentType,
          lastRequest: action.payload.request,
          error: null
        }
      }
      
    case 'CUSTOM_SECTION_SET_PASSAGES':
      return {
        ...state,
        customSection: {
          ...state.customSection,
          passages: action.payload.passages,
          questions: [], // Clear questions when setting passages
          contentType: 'passages',
          lastRequest: action.payload.request,
          error: null
        }
      }
      
    case 'CUSTOM_SECTION_CLEAR':
      return {
        ...state,
        customSection: {
          ...initialState.customSection
        }
      }
      
    // Full Test Actions
    case 'FULL_TEST_SET_REQUEST':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          testRequest: action.payload
        }
      }
      
    case 'FULL_TEST_SET_SHOW_COMPLETE':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          showCompleteTest: action.payload
        }
      }
      
    case 'FULL_TEST_SET_JOB_STATUS':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          jobStatus: action.payload
        }
      }
      
    case 'FULL_TEST_ADD_COMPLETED_SECTION':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          completedSections: [...state.fullTest.completedSections, action.payload]
        }
      }
      
    case 'FULL_TEST_SET_LOADING':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          loading: action.payload
        }
      }
      
    case 'FULL_TEST_SET_ERROR':
      return {
        ...state,
        fullTest: {
          ...state.fullTest,
          error: action.payload
        }
      }
      
    case 'FULL_TEST_CLEAR':
      return {
        ...state,
        fullTest: {
          ...initialState.fullTest
        }
      }
      
    // Preferences Actions
    case 'SET_SHOW_CHINESE':
      return {
        ...state,
        preferences: {
          ...state.preferences,
          showChinese: action.payload
        }
      }
      
    default:
      return state
  }
}

// Context creation
const AppStateContext = createContext<{
  state: AppState
  dispatch: React.Dispatch<AppAction>
} | undefined>(undefined)

// Provider component
export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appStateReducer, initialState)

  return (
    <AppStateContext.Provider value={{ state, dispatch }}>
      {children}
    </AppStateContext.Provider>
  )
}

// Custom hook to use the context
export function useAppState() {
  const context = useContext(AppStateContext)
  if (context === undefined) {
    throw new Error('useAppState must be used within an AppStateProvider')
  }
  return context
}

// Convenience hooks for specific parts of state
export function useCustomSectionState() {
  const { state, dispatch } = useAppState()
  return {
    ...state.customSection,
    dispatch
  }
}

export function useFullTestState() {
  const { state, dispatch } = useAppState()
  return {
    ...state.fullTest,
    dispatch
  }
}

export function usePreferences() {
  const { state, dispatch } = useAppState()
  return {
    ...state.preferences,
    dispatch
  }
}



// Helper hooks for custom section actions
export function useCustomSectionActions() {
  const { dispatch } = useAppState()
  
  return {
    setLoading: (loading: boolean) => 
      dispatch({ type: 'CUSTOM_SECTION_SET_LOADING', payload: loading }),
    
    setError: (error: string | null) => 
      dispatch({ type: 'CUSTOM_SECTION_SET_ERROR', payload: error }),
    
    setQuestions: (questions: Question[], contentType: 'questions' | 'prompts', request?: QuestionRequest) => 
      dispatch({ 
        type: 'CUSTOM_SECTION_SET_QUESTIONS', 
        payload: { questions, contentType, request } 
      }),
    
    setPassages: (passages: ReadingPassage[], request?: QuestionRequest) => 
      dispatch({ 
        type: 'CUSTOM_SECTION_SET_PASSAGES', 
        payload: { passages, request } 
      }),
    
    clearContent: () => 
      dispatch({ type: 'CUSTOM_SECTION_CLEAR' })
  }
}

// Helper hooks for full test actions
export function useFullTestActions() {
  const { dispatch } = useAppState()
  
  return {
    // test
    setTestRequest: (request: FullTestState['testRequest']) => 
      dispatch({ type: 'FULL_TEST_SET_REQUEST', payload: request }),
    
    // toggle between form view and progress view: setShowCompleteTest(true) → Show progress, setShowCompleteTest(false) → Show form
    setShowCompleteTest: (show: boolean) => 
      dispatch({ type: 'FULL_TEST_SET_SHOW_COMPLETE', payload: show }),
    
    setJobStatus: (status: any | null) => 
      dispatch({ type: 'FULL_TEST_SET_JOB_STATUS', payload: status }),
    
    addCompletedSection: (section: TestSection) => 
      dispatch({ type: 'FULL_TEST_ADD_COMPLETED_SECTION', payload: section }),
    
    setLoading: (loading: boolean) => 
      dispatch({ type: 'FULL_TEST_SET_LOADING', payload: loading }),
    
    setError: (error: string | null) => 
      dispatch({ type: 'FULL_TEST_SET_ERROR', payload: error }),
    
    clearFullTest: () => 
      dispatch({ type: 'FULL_TEST_CLEAR' })
  }
}