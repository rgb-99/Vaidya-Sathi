import Icon from './Icon.jsx'

export default function DemoPicker({ scenarios, value, onChange, disabled }) {
  if (!scenarios.length) return null
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <span className="flex items-center gap-1.5 text-xs text-muted"><Icon name="headphones" className="h-4 w-4" /> Try a demo:</span>
      {scenarios.map((s) => (
        <button key={s.id} disabled={disabled} onClick={() => onChange(s.id)}
          className={`chip px-3 py-1.5 text-xs ${value === s.id ? 'border-ink bg-ink text-bg hover:border-ink' : ''}`}>
          {s.title}
        </button>
      ))}
    </div>
  )
}
