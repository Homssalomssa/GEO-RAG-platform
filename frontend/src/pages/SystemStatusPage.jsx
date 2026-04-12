import { useState, useEffect } from 'react'

export default function SystemStatusPage({ onNavigate }) {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          const data = await response.json()
          setHealth(data)
        } else {
          setError('Failed to fetch system status')
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000) // Refresh every 5s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight text-on-surface font-headline mb-2">
          System Status
        </h1>
        <p className="text-on-surface-variant text-lg">Real-time monitoring of Geo-RAG platform services</p>
      </header>

      {loading && <p className="text-on-surface-variant">Loading system status...</p>}

      {error && (
        <div className="text-error text-sm p-4 bg-error/10 rounded-lg mb-6">{error}</div>
      )}

      {health && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Status Overview */}
          <div className="bg-surface-container-lowest rounded-xl p-8 border border-outline-variant/10 shadow-sm">
            <h3 className="font-headline font-bold text-lg mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">hub</span>
              Platform Status
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">Overall Status</span>
                <span className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full" />
                  <span className="font-semibold text-green-600">Online</span>
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">Vision Model</span>
                <span className="font-label text-on-surface">{health.vision_model || 'Qwen3-VL'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">LLM Model</span>
                <span className="font-label text-on-surface">{health.llm_model || 'Gemma 3'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-on-surface-variant">API Status</span>
                <span className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full" />
                  <span className="text-green-600">Ready</span>
                </span>
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="bg-surface-container-lowest rounded-xl p-8 border border-outline-variant/10 shadow-sm">
            <h3 className="font-headline font-bold text-lg mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">speed</span>
              Performance
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-on-surface-variant">Vector Latency</span>
                  <span className="font-label text-secondary font-bold">24ms</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-secondary h-full w-1/3 rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-on-surface-variant">API Response Time</span>
                  <span className="font-label text-primary font-bold">145ms</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-primary h-full w-1/2 rounded-full" />
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-on-surface-variant">Memory Usage</span>
                  <span className="font-label text-on-surface font-bold">62%</span>
                </div>
                <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                  <div className="bg-warning h-full w-3/5 rounded-full" />
                </div>
              </div>
            </div>
          </div>

          {/* Services */}
          <div className="bg-surface-container-lowest rounded-xl p-8 border border-outline-variant/10 shadow-sm lg:col-span-2">
            <h3 className="font-headline font-bold text-lg mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary">settings</span>
              Services
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex items-start gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full mt-1" />
                <div>
                  <p className="font-semibold text-on-surface">Vision Extractor</p>
                  <p className="text-xs text-on-surface-variant">Active • Processing</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full mt-1" />
                <div>
                  <p className="font-semibold text-on-surface">Retriever Worker</p>
                  <p className="text-xs text-on-surface-variant">Active • Ready</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full mt-1" />
                <div>
                  <p className="font-semibold text-on-surface">Answer Generator</p>
                  <p className="text-xs text-on-surface-variant">Active • Ready</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Back Button */}
      <button
        onClick={() => onNavigate('upload')}
        className="mt-8 flex items-center gap-2 px-5 py-2.5 rounded-xl text-primary font-semibold hover:bg-primary-fixed transition-colors"
      >
        <span className="material-symbols-outlined">arrow_back</span>
        Back to Upload
      </button>
    </div>
  )
}
