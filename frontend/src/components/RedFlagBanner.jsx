import Icon, { Spinner } from './Icon.jsx'

export default function RedFlagBanner({ flags, onPlay, busy }) {
  if (!flags.length) return null
  const urgent = flags.some((f) => f.severity === 'urgent')
  return (
    <div role="alert" className={`overflow-hidden rounded-3xl border-2 ${urgent ? 'border-red-500 bg-red-50 dark:bg-red-950/40' : 'border-amber-400 bg-amber-50 dark:bg-amber-950/40'}`}>
      <div className={`flex items-center gap-3 px-4 py-3 text-white ${urgent ? 'bg-red-600' : 'bg-amber-600'}`}>
        <Icon name="alert" className="h-6 w-6" />
        <span className="min-w-0 font-bold sm:text-lg">{urgent ? 'Danger signs found' : 'Warning signs found'}</span>
        <button onClick={onPlay} disabled={busy} className="ml-auto inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full bg-white/20 px-4 py-1.5 text-sm font-semibold hover:bg-white/30 disabled:opacity-60">
          {busy ? <Spinner className="h-4 w-4" /> : <Icon name="volume" className="h-4 w-4" />} Play alert
        </button>
      </div>
      <div className="divide-y divide-red-200 dark:divide-red-900/60">
        {flags.map((f) => (
          <div key={f.rule_id} className="px-4 py-3">
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-semibold">{f.title}</span>
              <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-white ${f.severity === 'urgent' ? 'bg-red-600' : 'bg-amber-600'}`}>{f.severity}</span>
              <span className="ml-auto font-mono text-[10px] text-muted">{f.rule_id}</span>
            </div>
            <div className="mt-0.5 font-medium">{f.action_text}</div>
            <div className="text-xs text-muted">Because: {f.matched_inputs.join(', ')}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
