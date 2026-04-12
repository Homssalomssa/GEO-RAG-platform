export default function Sidebar({ currentPage, onNavigate }) {
  const isActive = (page) => currentPage === page

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white dark:bg-slate-900 border-r border-outline-variant flex flex-col z-50 p-6">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-10">
        <div className="w-10 h-10 bg-primary-container rounded-xl flex items-center justify-center text-on-primary">
          <span className="material-symbols-outlined text-xl">satellite_alt</span>
        </div>
        <div>
          <h1 className="text-xl font-bold text-primary">Geo-RAG</h1>
          <p className="text-[10px] uppercase tracking-widest font-label text-outline">Satellite Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="space-y-1 flex-1">
        <button
          onClick={() => onNavigate('upload')}
          className={`w-full flex items-center gap-3 px-4 py-3 font-semibold border-r-4 rounded-lg transition-colors ${
            isActive('upload')
              ? 'text-primary bg-primary/5 border-primary'
              : 'text-on-surface-variant hover:text-primary border-transparent hover:bg-surface-container'
          }`}
        >
          <span className="material-symbols-outlined">cloud_upload</span>
          <span className="text-sm">Upload</span>
        </button>
        <button
          onClick={() => onNavigate('results')}
          className={`w-full flex items-center gap-3 px-4 py-3 font-semibold border-r-4 rounded-lg transition-colors ${
            isActive('results')
              ? 'text-primary bg-primary/5 border-primary'
              : 'text-on-surface-variant hover:text-primary border-transparent hover:bg-surface-container'
          }`}
        >
          <span className="material-symbols-outlined">analytics</span>
          <span className="text-sm">Results</span>
        </button>
        <button
          onClick={() => onNavigate('status')}
          className={`w-full flex items-center gap-3 px-4 py-3 font-semibold border-r-4 rounded-lg transition-colors ${
            isActive('status')
              ? 'text-primary bg-primary/5 border-primary'
              : 'text-on-surface-variant hover:text-primary border-transparent hover:bg-surface-container'
          }`}
        >
          <span className="material-symbols-outlined">settings_input_component</span>
          <span className="text-sm">System Status</span>
        </button>
      </nav>

      {/* Footer Button */}
      <button className="w-full py-3 px-4 bg-primary text-on-primary rounded-xl font-semibold flex items-center justify-center gap-2 hover:opacity-90 transition-all">
        <span className="material-symbols-outlined text-sm">add</span>
        <span>New Analysis</span>
      </button>
    </aside>
  )
}
