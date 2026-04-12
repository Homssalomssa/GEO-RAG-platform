export default function Card({ children, className = '', variant = 'default' }) {
  const baseClasses = 'bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/10'

  const variantClasses = {
    default: 'p-8',
    compact: 'p-6',
    minimal: 'p-4',
  }

  const classes = [baseClasses, variantClasses[variant], className].filter(Boolean).join(' ')

  return <div className={classes}>{children}</div>
}
