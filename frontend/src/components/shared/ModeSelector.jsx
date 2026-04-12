import { ANALYSIS_MODES, MODE_DESCRIPTIONS } from '../../utils/constants'

export default function ModeSelector({ value, onChange }) {
  return (
    <div className="space-y-3">
      {Object.values(ANALYSIS_MODES).map(mode => {
        const isActive = value === mode
        const description = MODE_DESCRIPTIONS[mode]
        const iconColor = mode === 'llm_only' ? 'text-outline' : mode === 'rag_baseline' ? 'text-secondary' : 'text-tertiary'

        return (
          <div
            key={mode}
            onClick={() => onChange(mode)}
            className={`p-4 rounded-xl border-2 flex items-start gap-4 cursor-pointer transition-all ${
              isActive
                ? 'border-tertiary-container bg-tertiary-container/5'
                : 'border-outline-variant hover:border-outline-variant/50 hover:bg-surface-container-low'
            }`}
          >
            {/* Radio Button */}
            <div className="mt-1 w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center" style={{borderColor: isActive ? 'rgb(95, 0, 228)' : 'rgb(114, 119, 132)'}}>
              {isActive && <div className="w-2.5 h-2.5 bg-tertiary-container rounded-full" />}
            </div>

            {/* Content */}
            <div className="flex-1">
              <h4 className={`text-sm font-bold flex items-center gap-2 ${isActive ? 'text-tertiary' : 'text-on-surface'}`}>
                {description.title}
                <span className={`material-symbols-outlined text-sm ${iconColor}`}>
                  {description.icon}
                </span>
              </h4>
              <p className="text-xs text-on-surface-variant mt-1">{description.description}</p>
              <p className="text-[10px] font-label text-outline-variant mt-2">{description.time}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
