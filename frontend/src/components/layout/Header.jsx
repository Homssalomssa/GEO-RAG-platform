export default function Header() {
  return (
    <header className="fixed top-0 right-0 w-[calc(100%-16rem)] bg-white/80 dark:bg-slate-950/80 backdrop-blur-md border-b border-outline-variant/20 flex justify-between items-center h-16 px-8 z-40">
      <div className="flex items-center gap-4">
        <h2 className="text-on-surface font-headline font-bold text-lg">Satellite Analysis Terminal</h2>
      </div>
      <div className="flex items-center gap-6">
        <div className="relative hidden lg:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-lg">search</span>
          <input
            className="bg-surface-container-low border-none rounded-full pl-10 pr-4 py-1.5 text-sm w-64 focus:ring-2 focus:ring-primary/20 focus:outline-none"
            placeholder="Search coordinates..."
            type="text"
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="text-on-surface-variant hover:text-primary transition-colors">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="text-on-surface-variant hover:text-primary transition-colors">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </div>
    </header>
  )
}
