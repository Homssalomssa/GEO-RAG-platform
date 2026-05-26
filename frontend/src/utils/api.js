import { API_BASE, POLLING_INTERVAL, MAX_POLLING_ATTEMPTS } from './constants'

/**
 * Submit an image for analysis
 */
﻿export async function submitAnalysis(file, question, mode, city = '') {
  const formData = new FormData()
  formData.append('image', file)
  formData.append('question', question)
  formData.append('mode', mode)
  if (city) {
    formData.append('city', city)
  }

  console.log('Submitting analysis:', {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
    question,
    mode,
    city: city || '(any)',
  })

  try {
    const response = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      body: formData,
    })

    console.log('Submit response status:', response.status)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Submit error response:', errorText)
      throw new Error(`Analysis submission failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    console.log('Submit response data:', data)
    return data.job_id
  } catch (error) {
    console.error('Submit error:', error)
    throw error
  }
}

export async function checkJobStatus(jobId) {
  try {
    const response = await fetch(`${API_BASE}/status/${jobId}`)

    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    console.log(`Status for ${jobId}:`, data)
    return data
  } catch (error) {
    console.error('Status check error:', error)
    throw error
  }
}

/**
 * Check system health
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`)
    return response.ok
  } catch (error) {
    console.error('Health check failed:', error)
    return false
  }
}

/**
 * Poll for job status until completion or timeout
 * Calls onProgress callback with each update
 * Resolves with final result on completion
 * Rejects with error on failure or timeout
 */
export async function pollJobStatus(jobId, onProgress) {
  let pollCount = 0

  console.log('Starting polling for job:', jobId)

  while (pollCount < MAX_POLLING_ATTEMPTS) {
    try {
      const statusData = await checkJobStatus(jobId)

      // Call progress callback with status and progress
      if (onProgress) {
        onProgress({
          progress: statusData.progress || 0,
          status: statusData.status,
          message: getProgressMessage(statusData),
        })
      }

      // Check if job is complete
      if (statusData.status === 'completed') {
        console.log('Job completed:', jobId)
        return {
          fileName: statusData.file_name || 'image',
          mode: statusData.mode || 'rag_baseline',
          answer: statusData.result || '',
          visionFeatures: statusData.vision_features || {},
          retrievedContext: statusData.retrieved_context || [],
          gisData: statusData.gis_data || {},
          timing: statusData.processing_seconds
            ? Math.round(statusData.processing_seconds * 1000)
            : 0,
        }
      }

      // Check if job failed
      if (statusData.status === 'failed') {
        console.error('Job failed:', statusData.error)
        throw new Error(`Analysis failed: ${statusData.error || 'Unknown error'}`)
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL))
      pollCount++
    } catch (error) {
      if (error.message.includes('Analysis failed')) {
        throw error
      }
      // Retry on network errors
      await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL))
      pollCount++
    }
  }

  throw new Error('Analysis timeout: job did not complete within timeout period')
}

/**
 * Generate progress message based on status and progress
 */
function getProgressMessage(statusData) {
  const status = statusData.status
  const progress = statusData.progress || 0

  if (status === 'queued') {
    return 'Queued for processing...'
  }
  if (status === 'processing') {
    if (progress < 25) return 'Extracting vision features...'
    if (progress < 50) return 'Retrieving knowledge...'
    if (progress < 75) return 'Generating analysis...'
    return 'Finalizing results...'
  }
  return 'Processing...'
}

