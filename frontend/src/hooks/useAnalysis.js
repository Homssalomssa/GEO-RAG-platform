import { useState, useCallback } from 'react'
import { submitAnalysis, pollJobStatus, checkHealth } from '../utils/api'

export function useAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [error, setError] = useState(null)

  const analyze = useCallback(async (files, question, mode, onResultAdded) => {
    setIsAnalyzing(true)
    setError(null)
    setProgress(0)

    try {
      // Process each file
      let completedCount = 0
      const results = []

      for (const fileObj of files) {
        try {
          setLoadingMessage(`Analyzing image ${completedCount + 1} of ${files.length}...`)

          // Submit image for analysis
          const jobId = await submitAnalysis(fileObj.file, question, mode)

          // Poll for results
          const result = await pollJobStatus(jobId, (progressData) => {
            // Update overall progress
            const overallProgress = ((completedCount + progressData.progress / 100) / files.length) * 100
            setProgress(Math.round(overallProgress))
            setLoadingMessage(progressData.message)
          })

          results.push(result)
          onResultAdded?.(result)

          completedCount++
        } catch (fileError) {
          console.error(`Error analyzing file ${completedCount + 1}:`, fileError)
          setError(fileError.message)
          throw fileError
        }
      }

      setProgress(100)
      setLoadingMessage('Analysis complete!')
      setIsAnalyzing(false)

      return results
    } catch (err) {
      setIsAnalyzing(false)
      setError(err.message || 'Analysis failed. Please try again.')
      throw err
    }
  }, [])

  const checkSystemHealth = useCallback(async () => {
    return await checkHealth()
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const reset = useCallback(() => {
    setIsAnalyzing(false)
    setProgress(0)
    setLoadingMessage('')
    setError(null)
  }, [])

  return {
    isAnalyzing,
    progress,
    loadingMessage,
    error,
    analyze,
    checkSystemHealth,
    clearError,
    reset,
  }
}
