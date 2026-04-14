import { useState } from 'react'
import Card from '../shared/Card'

export default function ResultCard({ result, index }) {
  const { fileName, answer, visionFeatures, retrievedContext, gisData, timing, imageUrl } = result
  const [showEvidence, setShowEvidence] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)
  const { conclusion, reasoning } = splitConclusionAndReasoning(answer)

  // Fallback hero image if preview not available
  const fallbackImageUrl = index === 0
    ? 'https://images.unsplash.com/photo-1446776653964-20c1d3a81b06?w=500&h=300&fit=crop'
    : 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=500&h=300&fit=crop'

  return (
    <div className="bg-surface-container-lowest rounded-xl p-0 overflow-hidden transition-all hover:shadow-lg flex flex-col">
      {/* Hero Image */}
      <div className="relative h-48 w-full overflow-hidden">
        <img className="w-full h-full object-cover" src={imageUrl || fallbackImageUrl} alt={fileName} />
        <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-transparent" />
        <div className="absolute top-4 left-4 flex gap-2">
          <div className="bg-white/90 backdrop-blur px-3 py-1 rounded-full text-[10px] font-label font-bold text-secondary uppercase tracking-tighter">
            {index === 0 ? 'Verified' : 'AI Insights'}
          </div>
        </div>
      </div>

      <div className="p-8 space-y-8">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-xl font-bold text-on-surface tracking-tight">{fileName}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="material-symbols-outlined text-sm text-outline">schedule</span>
              <span className="text-xs font-label text-on-surface-variant">Processed in {(timing / 1000).toFixed(1)}s</span>
            </div>
          </div>
          <button className="w-10 h-10 rounded-full hover:bg-surface-container flex items-center justify-center text-outline transition-colors">
            <span className="material-symbols-outlined">more_vert</span>
          </button>
        </div>

        {/* Reasoning Toggle */}
        {reasoning ? (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowReasoning((prev) => !prev)}
              className="flex items-center gap-2 text-sm font-semibold text-primary hover:opacity-80 transition-opacity"
            >
              <span className="material-symbols-outlined text-[18px]">
                {showReasoning ? 'expand_less' : 'expand_more'}
              </span>
              {showReasoning ? 'Hide reasoning' : 'Show reasoning'}
            </button>
          </div>
        ) : null}

        {/* Analysis Result Text */}
        <div className="bg-surface-container-low p-5 rounded-xl">
          <h4 className="text-xs font-label font-bold text-primary mb-2 uppercase tracking-widest">
            Model Conclusion
          </h4>
          <p className="text-on-surface leading-relaxed whitespace-pre-wrap">{conclusion || answer}</p>
          {showReasoning && reasoning ? (
            <div className="mt-4 pt-4 border-t border-outline-variant/20">
              <h5 className="text-[11px] font-label font-bold text-on-surface-variant mb-2 uppercase tracking-widest">
                Reasoning
              </h5>
              <p className="text-on-surface-variant leading-relaxed whitespace-pre-wrap">{reasoning}</p>
            </div>
          ) : null}
        </div>

        {/* Evidence Toggle */}
        {(visionFeatures && Object.keys(visionFeatures).length > 0) ||
        (retrievedContext && retrievedContext.length > 0) ||
        (gisData && Object.keys(gisData).length > 0) ? (
          <div className="pt-4 border-t border-outline-variant/10">
            <button
              type="button"
              onClick={() => setShowEvidence((prev) => !prev)}
              className="flex items-center gap-2 text-sm font-semibold text-primary hover:opacity-80 transition-opacity"
            >
              <span className="material-symbols-outlined text-[18px]">
                {showEvidence ? 'expand_less' : 'expand_more'}
              </span>
              {showEvidence ? 'Hide evidence' : 'Show evidence'}
            </button>
          </div>
        ) : null}

        {showEvidence && (
          <>
            {/* Vision Features */}
            {visionFeatures && Object.keys(visionFeatures).length > 0 && (
              <div>
                <h4 className="text-xs font-label font-bold text-on-surface-variant mb-3 uppercase tracking-widest">
                  Vision Features
                </h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(visionFeatures).map(([key]) => (
                    <div key={key} className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-high rounded-full">
                      <span className="material-symbols-outlined text-[18px] text-primary">
                        {getIconForFeature(key)}
                      </span>
                      <span className="text-xs font-semibold">{formatFeatureName(key)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Retrieved Knowledge */}
            {retrievedContext && retrievedContext.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-label font-bold text-on-surface-variant mb-3 uppercase tracking-widest">
                  Retrieved Knowledge
                </h4>
                {retrievedContext.slice(0, 2).map((context, idx) => (
                  <div
                    key={idx}
                    className="p-4 border-l-4 border-secondary bg-surface-container-low rounded-r-xl flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-secondary">description</span>
                      <div>
                        <p className="text-sm font-semibold">
                          {typeof context === 'string' ? 'Reference Document' : context.chunk?.slice(0, 50)}...
                        </p>
                        <p className="text-[10px] text-on-surface-variant">Knowledge Base Match</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] font-label font-bold text-secondary">
                        {typeof context === 'object' && context.score ? (Math.round(context.score * 100))+'%' : '85%'}
                      </span>
                      <div className="w-12 h-1 bg-secondary rounded-full mt-1" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* GIS Data */}
            {gisData && Object.keys(gisData).length > 0 && (
              <div className="pt-6 border-t border-outline-variant/10">
                <h4 className="text-xs font-label font-bold text-on-surface-variant mb-4 uppercase tracking-widest">
                  GIS Data
                </h4>
                <div className="grid grid-cols-2 gap-6">
                  {Object.entries(gisData).slice(0, 2).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-3">
                      <div className="p-2 bg-secondary/10 rounded-lg text-secondary">
                        <span className="material-symbols-outlined text-[20px]">
                          {getIconForGISField(key)}
                        </span>
                      </div>
                      <div>
                        <p className="text-[10px] text-on-surface-variant font-bold uppercase">
                          {formatGISFieldName(key)}
                        </p>
                        <p className="font-label text-sm text-on-surface">{String(value).slice(0, 30)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function getIconForFeature(key) {
  const iconMap = {
    color: 'palette',
    shape: 'category',
    object: 'shapes',
    texture: 'brush',
  }
  return iconMap[key.toLowerCase().split('_')[0]] || 'info'
}

function formatFeatureName(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function getIconForGISField(key) {
  const lowerKey = key.toLowerCase()
  if (lowerKey.includes('coord') || lowerKey.includes('location')) return 'location_on'
  if (lowerKey.includes('area') || lowerKey.includes('size')) return 'square_foot'
  if (lowerKey.includes('elevation') || lowerKey.includes('height')) return 'height'
  if (lowerKey.includes('time') || lowerKey.includes('date')) return 'calendar_today'
  return 'info'
}

function formatGISFieldName(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function splitConclusionAndReasoning(answer = '') {
  const text = String(answer || '').trim()
  if (!text) return { conclusion: '', reasoning: '' }

  // Structured format (our intended prompt style)
  const directAnswerMatch = text.match(
    /(?:^|\n)\s*(?:1[\)\.\-]?\s*)?Direct Answer:\s*([\s\S]*?)(?:\n\s*(?:(?:2[\)\.\-]?\s*)?(?:Key Evidence|Evidence):|(?:3[\)\.\-]?\s*)?Confidence:)|$)/i
  )
  const conclusion = directAnswerMatch ? directAnswerMatch[1].trim() : text

  const reasoningMatch = text.match(
    /(?:^|\n)\s*(?:(?:2[\)\.\-]?\s*)?(?:Key Evidence|Evidence):|(?:3[\)\.\-]?\s*)?Confidence:)[\s\S]*$/i
  )
  let reasoning = reasoningMatch ? reasoningMatch[0].trim() : ''

  // Fallback for unstructured model outputs:
  // use first sentence block as conclusion, rest as reasoning.
  if (!reasoning) {
    const sentenceSplit = text.split(/(?<=[.!?])\s+/)
    if (sentenceSplit.length > 1) {
      const fallbackConclusion = sentenceSplit.slice(0, 2).join(' ').trim()
      const fallbackReasoning = text.slice(fallbackConclusion.length).trim()
      return {
        conclusion: fallbackConclusion || text,
        reasoning: fallbackReasoning,
      }
    }
  }

  return { conclusion, reasoning }
}
