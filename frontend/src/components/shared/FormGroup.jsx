export default function FormGroup({
  label,
  children,
  helpText = null,
  error = null,
  className = '',
}) {
  return (
    <div className={`mb-8 ${className}`}>
      {label && (
        <label className="block text-xs font-label font-bold text-outline uppercase mb-2 tracking-wider">
          {label}
        </label>
      )}
      <div className="relative">{children}</div>
      {helpText && <p className="text-xs text-on-surface-variant mt-2">{helpText}</p>}
      {error && <p className="text-xs text-error mt-2">{error}</p>}
    </div>
  )
}
