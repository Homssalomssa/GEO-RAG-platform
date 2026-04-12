import Card from '../shared/Card'
import FormGroup from '../shared/FormGroup'
import ModeSelector from '../shared/ModeSelector'
import Button from '../shared/Button'
import { MAX_QUESTION_LENGTH } from '../../utils/constants'

export default function AnalysisSettings({
  question,
  onQuestionChange,
  mode,
  onModeChange,
  onAnalyze,
  isAnalyzing,
  hasFiles,
  systemInfo = {},
}) {
  const canAnalyze = hasFiles && question.trim().length > 0
  const charCount = question.length

  const {
    model = 'Orion-V4 (Geospatial)',
    latency = '24ms',
    usage = '84% Capacity',
  } = systemInfo

  return (
    <Card className="space-y-6">
      <h3 className="font-headline font-bold text-lg flex items-center gap-2">
        <span className="material-symbols-outlined text-secondary">settings_suggest</span>
        Analysis Settings
      </h3>

      {/* Question Input */}
      <FormGroup label="Analysis Objective">
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => onQuestionChange(e.target.value.slice(0, MAX_QUESTION_LENGTH))}
            className="w-full h-32 bg-surface-container-low border-none rounded-xl p-4 text-sm focus:ring-2 focus:ring-primary transition-all resize-none focus:outline-none text-on-surface placeholder-on-surface-variant"
            placeholder="e.g., What indicators of urban sprawl are visible in this area? Identify changes in vegetation coverage, infrastructure development, and water bodies."
          />
          <div className="absolute bottom-3 right-3 text-[10px] font-label text-outline">
            {charCount} / {MAX_QUESTION_LENGTH}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            className="text-[10px] font-label px-2 py-1 bg-surface-container hover:bg-surface-container-highest rounded text-on-surface-variant transition-colors"
            onClick={() => onQuestionChange('What is the surface area of this region and how has it changed?')}
          >
            Surface Area Calculation
          </button>
          <button
            type="button"
            className="text-[10px] font-label px-2 py-1 bg-surface-container hover:bg-surface-container-highest rounded text-on-surface-variant transition-colors"
            onClick={() => onQuestionChange('Analyze the vegetation health and compare with historical data.')}
          >
            Vegetation Health Index
          </button>
          <button
            type="button"
            className="text-[10px] font-label px-2 py-1 bg-surface-container hover:bg-surface-container-highest rounded text-on-surface-variant transition-colors"
            onClick={() => onQuestionChange('What infrastructure changes are visible in this area?')}
          >
            Infrastructure Change
          </button>
        </div>
      </FormGroup>

      {/* Mode Selector */}
      <FormGroup label="Analysis Engine">
        <ModeSelector value={mode} onChange={onModeChange} />
      </FormGroup>

      {/* Analyze Button */}
      <Button
        onClick={onAnalyze}
        disabled={!canAnalyze}
        loading={isAnalyzing}
        icon="bolt"
        size="lg"
      >
        Execute Analysis
      </Button>

      {/* Estimate Info */}
      <p className="text-center text-[10px] font-label text-outline">
        ESTIMATED COST: <span className="text-on-surface font-bold">12.5 CREDITS</span> | TIME:{' '}
        <span className="text-on-surface font-bold">~45 SEC</span>
      </p>

      {/* System Parameters */}
      <div className="bg-surface-container rounded-xl p-6">
        <h4 className="text-xs font-label font-bold text-outline uppercase mb-4 tracking-wider">
          System Parameters
        </h4>
        <div className="space-y-3">
          <div className="flex justify-between items-center text-xs">
            <span className="text-on-surface-variant">Active Model</span>
            <span className="font-label text-on-surface">{model}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-on-surface-variant">Vector Latency</span>
            <span className="font-label text-secondary">{latency}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-on-surface-variant">API Token Usage</span>
            <span className="font-label text-on-surface">{usage}</span>
          </div>
        </div>
      </div>

      {/* AI Recommendation - Only show if question is short */}
      {question.length === 0 && (
        <div className="bg-tertiary/5 rounded-xl p-6 border border-tertiary/10 flex gap-4">
          <span className="material-symbols-outlined text-tertiary shrink-0">auto_awesome</span>
          <div>
            <h4 className="text-sm font-bold text-tertiary mb-1">Pro Tip</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              Start by asking specific questions about the satellite imagery. For example, ask about vegetation patterns, urban development, water bodies, or infrastructure changes you want to analyze.
            </p>
          </div>
        </div>
      )}
    </Card>
  )
}
