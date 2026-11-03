export default function RedFlagBanner({ flags, onPlay }) {
  if (!flags.length) return null
  return (
    <div className="space-y-1.5" role="alert">
      {flags.map((f) => (
        <div key={f.rule_id} className={`rounded-lg border px-3 py-1.5 ${f.severity === 'urgent' ? 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/40' : 'border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40'}`}>
          <div className="flex items-center gap-2 text-sm">
            <span className={`shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-white ${f.severity === 'urgent' ? 'bg-red-700' : 'bg-amber-600'}`}>{f.severity}</span>
            <span className="font-semibold">{f.title}</span>
            <span className="truncate font-medium">{f.action_text}</span>
            <span className="ml-auto shrink-0 font-mono text-[10px] text-muted">{f.rule_id}</span>
          </div>
          <div className="text-xs text-muted">Matched: {f.matched_inputs.join(', ')}</div>
        </div>
      ))}
      <button onClick={onPlay} className="btn-danger px-3 py-1 text-xs">Play alert</button>
    </div>
  )
}
