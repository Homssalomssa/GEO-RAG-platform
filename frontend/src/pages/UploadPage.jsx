import UploadZone from '../components/upload/UploadZone'
import ImageGrid from '../components/upload/ImageGrid'
import AnalysisSettings from '../components/upload/AnalysisSettings'

export default function UploadPage({
  question,
  onQuestionChange,
  mode,
  onModeChange,
  files,
  onFilesSelected,
  onRemoveFile,
  onAnalyze,
  isAnalyzing,
  systemInfo,
}) {
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight text-on-surface font-headline mb-2">
          Analyze Satellite Imagery
        </h1>
        <p className="text-on-surface-variant text-lg max-w-2xl">
          Deploy state-of-the-art Geo-RAG models to extract actionable insights from multi-spectral orbital data.
        </p>
      </header>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Upload Zone */}
        <section className="lg:col-span-7 space-y-6">
          <UploadZone onFilesSelected={onFilesSelected} fileCount={files.length} />
          {files.length > 0 && <ImageGrid files={files} onRemove={onRemoveFile} />}
        </section>

        {/* Right Column: Settings */}
        <aside className="lg:col-span-5 space-y-6">
          <AnalysisSettings
            question={question}
            onQuestionChange={onQuestionChange}
            mode={mode}
            onModeChange={onModeChange}
            onAnalyze={onAnalyze}
            isAnalyzing={isAnalyzing}
            hasFiles={files.length > 0}
            systemInfo={systemInfo}
          />
        </aside>
      </div>
    </div>
  )
}
