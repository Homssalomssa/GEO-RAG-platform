export default function ImageGrid({ files, onRemove }) {
  if (files.length === 0) return null

  return (
    <div className="mt-8">
      <p className="text-xs font-label font-bold text-outline uppercase mb-4 tracking-wider">
        Previews: {files.length} images
      </p>
      <div className="grid grid-cols-4 gap-4">
        {files.map((file, index) => (
          <div
            key={index}
            className="aspect-square rounded-lg bg-surface-container overflow-hidden relative group border border-outline-variant/20"
          >
            {file.preview && (
              <img
                src={file.preview}
                alt={`Preview ${index + 1}`}
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
              <button
                onClick={() => onRemove(index)}
                className="bg-white p-1 rounded-full text-error shadow-md hover:bg-error hover:text-white transition-colors"
                type="button"
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          </div>
        ))}
        {/* Add more button */}
        <div className="aspect-square rounded-lg border-2 border-dashed border-outline-variant flex items-center justify-center text-outline-variant hover:text-outline hover:border-outline cursor-pointer transition-all">
          <span className="material-symbols-outlined">add</span>
        </div>
      </div>
    </div>
  )
}
