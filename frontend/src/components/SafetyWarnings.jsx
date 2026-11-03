export default function SafetyWarnings({ warnings }) {
  if (!warnings?.length) return null
  return (
    <div className="space-y-2" role="alert">
      {warnings.map((w, i) => (
        <div key={w.rule_id + i} className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm">
          <div className="font-semibold">{w.title}</div>
          <div className="text-muted">{w.matched_inputs.join(', ')}</div>
          <div>{w.action_text}</div>
        </div>
      ))}
      <p className="text-xs text-muted">Prescription safety warnings are for the clinician only. Nothing was changed.</p>
    </div>
  )
}
