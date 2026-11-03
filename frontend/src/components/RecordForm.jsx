const VITALS = [['bp', 'BP'], ['temp', 'Temp °F'], ['pulse', 'Pulse'], ['spo2', 'SpO2'], ['resp_rate', 'Resp rate'], ['sugar', 'Sugar']]
const RX = [['drug', 'Drug'], ['dose', 'Dose'], ['frequency', 'Frequency'], ['timing', 'Timing'], ['duration', 'Duration']]

const Field = ({ label, children, className = '' }) => (
  <label className={`block ${className}`}><span className="label">{label}</span>{children}</label>
)

// Compact: the whole record fits one screen. Edits re-run the red-flag and safety rules (see App.jsx).
export default function RecordForm({ record, onChange, locked }) {
  const set = (patch) => onChange({ ...record, ...patch })
  const setRx = (i, k, v) => set({ prescription: record.prescription.map((r, j) => (j === i ? { ...r, [k]: v } : r)) })
  const lines = (arr) => arr.join('\n')
  const unlines = (s) => s.split('\n').filter((x) => x.trim())
  const t = (value, onChangeFn, extra = {}) => <input className="input" disabled={locked} value={value} onChange={(e) => onChangeFn(e.target.value)} {...extra} />

  return (
    <div className="space-y-2.5">
      <div className="grid grid-cols-12 gap-2">
        <Field label="Patient name" className="col-span-4">{t(record.patient.name, (v) => set({ patient: { ...record.patient, name: v } }))}</Field>
        <Field label="Age" className="col-span-2">{t(record.patient.age, (v) => set({ patient: { ...record.patient, age: v } }))}</Field>
        <Field label="Sex" className="col-span-2">{t(record.patient.sex, (v) => set({ patient: { ...record.patient, sex: v } }))}</Field>
        <Field label="Diagnosis" className="col-span-4">{t(record.diagnosis, (v) => set({ diagnosis: v }))}</Field>
      </div>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
        {VITALS.map(([k, label]) => <Field key={k} label={label}>{t(record.vitals[k], (v) => set({ vitals: { ...record.vitals, [k]: v } }))}</Field>)}
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Field label="Chief complaints (one per line)">
          <textarea className="input" rows={2} disabled={locked} value={lines(record.chief_complaints)} onChange={(e) => set({ chief_complaints: unlines(e.target.value) })} />
        </Field>
        <Field label="Advice (one per line)">
          <textarea className="input" rows={2} disabled={locked} value={lines(record.advice)} onChange={(e) => set({ advice: unlines(e.target.value) })} />
        </Field>
      </div>
      <div>
        <div className="mb-0.5 flex items-center justify-between">
          <span className="label mb-0">Prescription</span>
          <button disabled={locked} className="link text-xs"
            onClick={() => set({ prescription: [...record.prescription, { drug: '', dose: '', frequency: '', timing: '', duration: '' }] })}>+ Add medicine</button>
        </div>
        <div className="space-y-1">
          {record.prescription.map((rx, i) => (
            <div key={i} className="grid grid-cols-[1.3fr_0.8fr_1fr_1.3fr_0.9fr_auto] items-center gap-1.5">
              {RX.map(([k, label]) => (
                <input key={k} placeholder={label} aria-label={label} className="input" disabled={locked} value={rx[k]} onChange={(e) => setRx(i, k, e.target.value)} />
              ))}
              <button disabled={locked} aria-label="Remove medicine" title="Remove" className="link px-1 text-sm no-underline"
                onClick={() => set({ prescription: record.prescription.filter((_, j) => j !== i) })}>✕</button>
            </div>
          ))}
          {!record.prescription.length && <p className="text-xs text-muted">No medicines in this record.</p>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Allergies (one per line; checked against the prescription)">
          <textarea className="input" rows={1} disabled={locked} value={lines(record.allergies)} onChange={(e) => set({ allergies: unlines(e.target.value) })} />
        </Field>
        <Field label="Follow-up">{t(record.follow_up, (v) => set({ follow_up: v }))}</Field>
      </div>
    </div>
  )
}
