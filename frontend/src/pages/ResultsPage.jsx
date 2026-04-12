import LoadingProgress from '../components/results/LoadingProgress'
import ResultCard from '../components/results/ResultCard'

export default function ResultsPage({
  onNavigate,
  isAnalyzing = false,
  progress = 0,
  loadingMessage = '',
  results = [],
}) {
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-4xl font-extrabold text-on-surface tracking-tight mb-2">Analysis Results</h1>
          <p className="text-on-surface-variant font-label text-sm uppercase tracking-widest">
            Active Session: Q4-SURVEY-{new Date().getFullYear()}
          </p>
        </div>
        <button
          onClick={() => onNavigate('upload')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-primary font-semibold hover:bg-primary-fixed transition-colors"
        >
          <span className="material-symbols-outlined">arrow_back</span>
          Back to Upload
        </button>
      </div>

      {/* Loading State */}
      {isAnalyzing && <LoadingProgress progress={progress} message={loadingMessage} />}

      {/* Results Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {results.map((result, index) => (
          <ResultCard key={index} result={result} index={index} />
        ))}
      </div>

      {/* Empty State */}
      {results.length === 0 && !isAnalyzing && (
        <div className="text-center py-12">
          <p className="text-on-surface-variant">No results yet. Go back to upload to start an analysis.</p>
        </div>
      )}
    </div>
  )
}
