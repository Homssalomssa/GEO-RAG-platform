import { useState } from 'react'
import Card from '../shared/Card'

export default function UploadZone({ onFilesSelected, fileCount = 0 }) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    onFilesSelected(files)
  }

  const handleInputChange = (e) => {
    const files = Array.from(e.target.files)
    onFilesSelected(files)
  }

  return (
    <Card className="min-h-[500px] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-headline font-bold text-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">layers</span>
          Source Imagery
        </h3>
        <span className="text-xs font-label text-outline bg-surface-container-low px-2 py-1 rounded">
          UP TO 10MB
        </span>
      </div>

      {/* Upload Area */}
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`flex-grow border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-12 group cursor-pointer transition-all ${
          isDragging
            ? 'border-tertiary bg-tertiary/5'
            : 'border-outline-variant hover:border-tertiary hover:bg-tertiary/5'
        }`}
      >
        <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
          <span className="material-symbols-outlined text-3xl text-tertiary">upload_file</span>
        </div>
        <p className="text-on-surface font-semibold mb-1">Drop JPEG, PNG, TIFF or WebP here</p>
        <p className="text-on-surface-variant text-sm mb-6">or click to browse local files</p>
        <div className="flex gap-2">
          <div className="px-3 py-1 bg-secondary-container text-on-secondary-container text-[10px] font-label font-bold rounded-full">
            SENTINEL-2
          </div>
          <div className="px-3 py-1 bg-secondary-container text-on-secondary-container text-[10px] font-label font-bold rounded-full">
            LANDSAT-9
          </div>
          <div className="px-3 py-1 bg-secondary-container text-on-secondary-container text-[10px] font-label font-bold rounded-full">
            PLANET
          </div>
        </div>
        <input
          type="file"
          multiple
          onChange={handleInputChange}
          accept="image/jpeg,image/png,image/tiff,image/webp"
          className="hidden"
        />
      </label>

      {/* File Count */}
      {fileCount > 0 && (
        <p className="text-xs font-label font-bold text-outline uppercase mt-8 mb-4 tracking-wider">
          Queue: {fileCount} files selected
        </p>
      )}
    </Card>
  )
}
