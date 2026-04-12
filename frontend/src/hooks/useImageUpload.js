import { useState, useCallback } from 'react'
import { MAX_FILE_SIZE, ALLOWED_FILE_TYPES } from '../utils/constants'

export function useImageUpload() {
  const [files, setFiles] = useState([])
  const [error, setError] = useState(null)

  const validateFile = useCallback((file) => {
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      setError(`Unsupported file type: ${file.type}. Please use JPEG, PNG, TIFF, or WebP.`)
      return false
    }
    if (file.size > MAX_FILE_SIZE) {
      setError(`File too large: ${(file.size / 1024 / 1024).toFixed(1)}MB. Maximum size is 10MB.`)
      return false
    }
    return true
  }, [])

  const addFiles = useCallback(
    (newFiles) => {
      setError(null)
      const validFiles = []

      for (const file of newFiles) {
        if (validateFile(file)) {
          const reader = new FileReader()
          reader.onload = (e) => {
            setFiles((prev) => [
              ...prev,
              {
                file,
                name: file.name,
                size: file.size,
                preview: e.target.result,
              },
            ])
          }
          reader.readAsDataURL(file)
          validFiles.push(file)
        }
      }

      return validFiles
    },
    [validateFile]
  )

  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
    setError(null)
  }, [])

  const clearFiles = useCallback(() => {
    setFiles([])
    setError(null)
  }, [])

  return {
    files,
    error,
    addFiles,
    removeFile,
    clearFiles,
  }
}
