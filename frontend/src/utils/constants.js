// API Configuration
export const API_BASE = '/api'
export const POLLING_INTERVAL = 500 // ms
export const MAX_POLLING_ATTEMPTS = 300 // ~2.5 minutes

// File Upload Configuration
export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
export const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/tiff', 'image/webp']
export const MAX_QUESTION_LENGTH = 500

// Analysis Modes
export const ANALYSIS_MODES = {
  LLM_ONLY: 'llm_only',
  RAG_BASELINE: 'rag_baseline',
  RAG_ADVANCED: 'rag_advanced',
}

export const MODE_DESCRIPTIONS = {
  [ANALYSIS_MODES.LLM_ONLY]: {
    title: 'LLM Direct',
    description: 'General descriptive analysis using vision-capable base models.',
    time: '~3-5s',
    icon: 'bolt',
  },
  [ANALYSIS_MODES.RAG_BASELINE]: {
    title: 'RAG Baseline',
    description: 'Includes context from local GIS databases and topology records.',
    time: '~6-10s',
    icon: 'database',
  },
  [ANALYSIS_MODES.RAG_ADVANCED]: {
    title: 'RAG Advanced',
    description: 'Deep cross-referencing with global satellite archives and AI-derived vector data.',
    time: '~10-15s',
    icon: 'auto_fix_high',
  },
}
