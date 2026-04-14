import { useState, useEffect } from 'react'
import MainLayout from './components/layout/MainLayout'
import UploadPage from './pages/UploadPage'
import ResultsPage from './pages/ResultsPage'
import SystemStatusPage from './pages/SystemStatusPage'
import { submitAnalysis, pollJobStatus, checkHealth } from './utils/api'

export default function App() {
  const [currentPage, setCurrentPage] = useState('upload')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState('rag_baseline')
  const [results, setResults] = useState([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [systemInfo, setSystemInfo] = useState({})

  // Fetch system info on mount
  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          const data = await response.json()
          setSystemInfo({
            model: data.model || 'Orion-V4 (Geospatial)',
            latency: data.latency || '24ms',
            usage: data.api_usage || '84% Capacity',
          })
        }
      } catch (error) {
        console.warn('Could not fetch system info:', error)
      }
    }
    fetchSystemInfo()
    const interval = setInterval(fetchSystemInfo, 30000)
    return () => clearInterval(interval)
  }, [])

  // Handle file selection
  const handleFilesSelected = (newFiles) => {
    const fileObjs = []
    newFiles.forEach((file) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          fileObjs.push({
            file,
            name: file.name,
            preview: e.target.result,
          })
          setUploadedFiles((prev) => [...prev, { file, name: file.name, preview: e.target.result }])
        }
        reader.readAsDataURL(file)
      }
    })
  }

  // Handle file removal
  const handleRemoveFile = (index) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  // Handle analysis
  const handleAnalyze = async () => {
    if (uploadedFiles.length === 0 || !question.trim()) return

    setIsAnalyzing(true)
    setProgress(0)
    setResults([])
    setCurrentPage('results')

    try {
      let completedCount = 0

      for (const fileObj of uploadedFiles) {
        try {
          setLoadingMessage(`Analyzing image ${completedCount + 1} of ${uploadedFiles.length}...`)

          // Submit image for analysis
          const jobId = await submitAnalysis(fileObj.file, question, mode)

          // Poll for results
          const result = await pollJobStatus(jobId, (progressData) => {
            const overallProgress = ((completedCount + progressData.progress / 100) / uploadedFiles.length) * 100
            setProgress(Math.round(overallProgress))
            setLoadingMessage(progressData.message)
          })

          const resultWithImage = {
            ...result,
            fileName: fileObj.name || result.fileName || 'image',
            imageUrl: fileObj.preview || null,
          }

          setResults((prev) => [...prev, resultWithImage])
          completedCount++
        } catch (fileError) {
          console.error(`Error analyzing file ${completedCount + 1}:`, fileError)
          setLoadingMessage(`Error: ${fileError.message}`)
          break
        }
      }

      setProgress(100)
      setLoadingMessage('Analysis complete!')
    } catch (err) {
      console.error('Analysis failed:', err)
      setLoadingMessage(`Failed: ${err.message}`)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Handle navigation
  const handleNavigate = (page) => {
    setCurrentPage(page)
  }

  // Handle going back to upload
  const handleBackToUpload = () => {
    setCurrentPage('upload')
    setQuestion('')
    setResults([])
    setUploadedFiles([])
  }

  return (
    <MainLayout currentPage={currentPage} onNavigate={handleNavigate}>
      {currentPage === 'upload' && (
        <UploadPage
          question={question}
          onQuestionChange={setQuestion}
          mode={mode}
          onModeChange={setMode}
          files={uploadedFiles}
          onFilesSelected={handleFilesSelected}
          onRemoveFile={handleRemoveFile}
          onAnalyze={handleAnalyze}
          isAnalyzing={isAnalyzing}
          systemInfo={systemInfo}
        />
      )}

      {currentPage === 'results' && (
        <ResultsPage
          onNavigate={handleBackToUpload}
          isAnalyzing={isAnalyzing}
          progress={progress}
          loadingMessage={loadingMessage}
          results={results}
        />
      )}

      {currentPage === 'status' && <SystemStatusPage onNavigate={handleNavigate} />}
    </MainLayout>
  )
}
