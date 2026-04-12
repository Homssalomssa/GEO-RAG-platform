export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  icon = null,
  className = '',
  ...props
}) {
  const baseClasses = 'font-semibold rounded-xl transition-all flex items-center justify-center gap-2'

  const variantClasses = {
    primary: 'bg-gradient-to-r from-primary to-primary-container text-on-primary hover:shadow-lg shadow-primary/20 disabled:opacity-50',
    secondary: 'bg-surface-container text-on-surface hover:bg-surface-container-high border border-outline-variant/30',
    ghost: 'text-primary hover:bg-primary-fixed',
  }

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg w-full',
  }

  const classes = [baseClasses, variantClasses[variant], sizeClasses[size], className]
    .filter(Boolean)
    .join(' ')

  return (
    <button className={classes} disabled={disabled || loading} {...props}>
      {loading && <span className="material-symbols-outlined animate-spin">sync</span>}
      {icon && !loading && <span className="material-symbols-outlined text-lg">{icon}</span>}
      {children}
    </button>
  )
}
