export default function RedFlagBanner({ flags, onPlay }) {
  if (!flags.length) return null
  return (
    <div className="space-y-2">
      {flags.map((f) => (
        <div key={f.rule_id} className={`rounded p-3 border-l-8 ${f.severity === 'urgent' ? 'bg-red-100 border-red-600' : 'bg-amber-100 border-amber-500'}`}>
          <div className="font-bold">{f.title} <span className="text-xs uppercase">({f.severity}, {f.rule_id})</span></div>
          <div className="text-sm">Matched: {f.matched_inputs.join(', ')}</div>
          <div className="font-semibold">{f.action_text}</div>
        </div>
      ))}
      <button onClick={onPlay} className="bg-red-700 text-white rounded px-3 py-1">Play alert</button>
    </div>
  )
}
