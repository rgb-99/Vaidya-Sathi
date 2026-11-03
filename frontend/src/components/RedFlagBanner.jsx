export default function RedFlagBanner({ flags, onPlay }) {
  if (!flags.length) return null
  return (
    <div className="space-y-2" role="alert">
      {flags.map((f) => (
        <div key={f.rule_id} className={`rounded-xl border p-4 ${f.severity === 'urgent' ? 'bg-red-50 border-red-300' : 'bg-amber-50 border-amber-300'}`}>
          <div className="flex items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider text-white ${f.severity === 'urgent' ? 'bg-red-700' : 'bg-amber-600'}`}>{f.severity}</span>
            <span className="font-semibold">{f.title}</span>
            <span className="ml-auto font-mono text-xs text-muted">{f.rule_id}</span>
          </div>
          <div className="mt-1 text-sm text-muted">Matched: {f.matched_inputs.join(', ')}</div>
          <div className="mt-1 font-medium">{f.action_text}</div>
        </div>
      ))}
      <button onClick={onPlay} className="btn-danger">Play alert</button>
    </div>
  )
}
