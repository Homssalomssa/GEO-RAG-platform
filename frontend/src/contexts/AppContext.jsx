import React, { createContext, useReducer, useCallback } from 'react'

export const AppContext = createContext()

const initialState = {
  // Upload form
  uploadedFiles: [],
  analysisQuestion: '',
  selectedMode: 'rag_baseline',

  // Analysis state
  isAnalyzing: false,
  currentJobIds: [],
  progress: 0,
  loadingMessage: 'Preparing analysis...',

  // Results
  results: [],
  error: null,

  // UI state
  currentPage: 'upload', // 'upload' | 'results'
}

function appReducer(state, action) {
  switch (action.type) {
    case 'SET_UPLOADED_FILES':
      return { ...state, uploadedFiles: action.payload }

    case 'REMOVE_FILE':
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.filter((_, i) => i !== action.payload),
      }

    case 'SET_QUESTION':
      return { ...state, analysisQuestion: action.payload }

    case 'SET_MODE':
      return { ...state, selectedMode: action.payload }

    case 'START_ANALYSIS':
      return {
        ...state,
        isAnalyzing: true,
        currentJobIds: action.payload,
        progress: 0,
        results: [],
        error: null,
        currentPage: 'results',
        loadingMessage: 'Preparing analysis...',
      }

    case 'UPDATE_PROGRESS':
      return {
        ...state,
        progress: action.payload.progress,
        loadingMessage: action.payload.message,
      }

    case 'ADD_RESULT':
      return {
        ...state,
        results: [...state.results, action.payload],
      }

    case 'ANALYSIS_COMPLETE':
      return {
        ...state,
        isAnalyzing: false,
      }

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isAnalyzing: false,
      }

    case 'CLEAR_ERROR':
      return { ...state, error: null }

    case 'GO_TO_UPLOAD':
      return {
        ...state,
        currentPage: 'upload',
        uploadedFiles: [],
        analysisQuestion: '',
        results: [],
        error: null,
      }

    case 'GO_TO_RESULTS':
      return { ...state, currentPage: 'results' }

    case 'RESET':
      return initialState

    default:
      return state
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState)

  const setUploadedFiles = useCallback(
    (files) => dispatch({ type: 'SET_UPLOADED_FILES', payload: files }),
    []
  )

  const removeFile = useCallback(
    (index) => dispatch({ type: 'REMOVE_FILE', payload: index }),
    []
  )

  const setAnalysisQuestion = useCallback(
    (question) => dispatch({ type: 'SET_QUESTION', payload: question }),
    []
  )

  const setSelectedMode = useCallback(
    (mode) => dispatch({ type: 'SET_MODE', payload: mode }),
    []
  )

  const startAnalysis = useCallback(
    (jobIds) => dispatch({ type: 'START_ANALYSIS', payload: jobIds }),
    []
  )

  const updateProgress = useCallback(
    (progress, message) =>
      dispatch({ type: 'UPDATE_PROGRESS', payload: { progress, message } }),
    []
  )

  const addResult = useCallback(
    (result) => dispatch({ type: 'ADD_RESULT', payload: result }),
    []
  )

  const analysisComplete = useCallback(
    () => dispatch({ type: 'ANALYSIS_COMPLETE' }),
    []
  )

  const setError = useCallback(
    (error) => dispatch({ type: 'SET_ERROR', payload: error }),
    []
  )

  const clearError = useCallback(() => dispatch({ type: 'CLEAR_ERROR' }), [])

  const goToUpload = useCallback(() => dispatch({ type: 'GO_TO_UPLOAD' }), [])

  const goToResults = useCallback(() => dispatch({ type: 'GO_TO_RESULTS' }), [])

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  const value = {
    state,
    setUploadedFiles,
    removeFile,
    setAnalysisQuestion,
    setSelectedMode,
    startAnalysis,
    updateProgress,
    addResult,
    analysisComplete,
    setError,
    clearError,
    goToUpload,
    goToResults,
    reset,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useAppContext() {
  const context = React.useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider')
  }
  return context
}
