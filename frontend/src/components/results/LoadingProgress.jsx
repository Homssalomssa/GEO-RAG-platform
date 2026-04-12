export default function LoadingProgress({ progress, message }) {
  return (
    <div className="mb-12 p-8 bg-surface-container-lowest rounded-xl border border-outline-variant/10 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 flex items-center justify-center rounded-full bg-tertiary/10 text-tertiary">
            <span className="material-symbols-outlined animate-spin">sync</span>
          </div>
          <div>
            <h4 className="font-bold text-on-surface">Processing Satellite Data</h4>
            <p className="text-sm text-on-surface-variant">{message}</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs font-label text-tertiary font-bold">{progress}% COMPLETE</span>
        </div>
      </div>
      <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
        <div
          className="bg-tertiary h-full rounded-full shadow-[0_0_8px_rgba(95,0,228,0.4)] transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
