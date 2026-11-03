import Icon from './Icon.jsx'

export default function SafetyWarnings({ warnings }) {
  if (!warnings?.length) return null
  return (
    <div className="space-y-2 rounded-3xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/40" role="alert">
      <div className="flex items-center gap-2 font-semibold text-amber-900 dark:text-amber-200"><Icon name="pill" className="h-5 w-5" /> Check these medicines</div>
      {warnings.map((w, i) => (
        <div key={w.rule_id + i} className="text-sm">
          <div className="font-semibold">{w.title}</div>
          <div>{w.action_text}</div>
          <div className="text-xs text-muted">{w.matched_inputs.join(', ')}</div>
        </div>
      ))}
      <p className="text-xs text-muted">Prescription safety warnings are for the clinician only. Nothing was changed.</p>
    </div>
  )
}
