import Icon from './Icon.jsx'

const STYLE = {
  clinician: 'mr-8 rounded-bl-md bg-accent-soft',
  patient: 'ml-8 rounded-br-md bg-green-50 dark:bg-green-950/40',
  unknown: 'mr-8 rounded-bl-md bg-bg',
}
const LABEL = { clinician: 'Doctor', patient: 'Patient', unknown: 'Speaker?' }

// Speaker turns shown as chat bubbles: doctor on the left, patient on the right.
export default function DiarizedTranscript({ utterances, onSwap }) {
  if (!utterances.length) return null
  const known = utterances.some((u) => u.speaker !== 'unknown')
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="label mb-0">Who said what</span>
        {known
          ? <button className="chip px-3 py-1 text-xs" onClick={onSwap}><Icon name="swap" className="h-3.5 w-3.5" /> Swap doctor / patient</button>
          : <span className="text-xs text-muted">Roles unclear: extraction ignores speakers</span>}
      </div>
      {utterances.map((u) => (
        <div key={u.id} className={`rounded-2xl px-4 py-2.5 text-[15px] ${STYLE[u.speaker]}`}>
          <div className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider text-muted">{LABEL[u.speaker]}</div>
          {u.text}
        </div>
      ))}
    </div>
  )
}
