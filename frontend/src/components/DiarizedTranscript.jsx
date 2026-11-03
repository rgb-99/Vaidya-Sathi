const STYLE = {
  clinician: 'border-accent bg-accent-soft',
  patient: 'border-green-600 bg-green-50',
  unknown: 'border-line bg-bg',
}
const LABEL = { clinician: 'Clinician', patient: 'Patient', unknown: 'Speaker?' }

export default function DiarizedTranscript({ utterances, onSwap }) {
  if (!utterances.length) return null
  const known = utterances.some((u) => u.speaker !== 'unknown')
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="label mb-0">Speakers</span>
        {known
          ? <button className="link text-xs" onClick={onSwap}>Swap roles</button>
          : <span className="text-xs text-muted">Roles unclear: extraction ignores speakers</span>}
      </div>
      {utterances.map((u) => (
        <div key={u.id} className={`rounded-lg border-l-4 px-3 py-2 text-sm ${STYLE[u.speaker]}`}>
          <div className="font-mono text-[11px] uppercase tracking-wider text-muted">{LABEL[u.speaker]}</div>
          {u.text}
        </div>
      ))}
    </div>
  )
}
