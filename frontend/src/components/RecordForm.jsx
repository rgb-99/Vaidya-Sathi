const VITALS = ['bp', 'temp', 'spo2', 'pulse', 'resp_rate', 'sugar']
const RX_FIELDS = ['drug', 'dose', 'frequency', 'timing', 'duration']

const Field = ({ label, children }) => (
  <label className="block"><span className="label">{label}</span>{children}</label>
)

export default function RecordForm({ record, onChange, locked }) {
  const set = (patch) => onChange({ ...record, ...patch })
  const setRx = (i, k, v) => set({ prescription: record.prescription.map((r, j) => (j === i ? { ...r, [k]: v } : r)) })
  const lines = (arr) => arr.join('\n')
  const unlines = (s) => s.split('\n').filter((x) => x.trim())

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {['name', 'age', 'sex'].map((k) => (
          <Field key={k} label={`Patient ${k}`}>
            <input className="input" disabled={locked} value={record.patient[k]} onChange={(e) => set({ patient: { ...record.patient, [k]: e.target.value } })} />
          </Field>
        ))}
      </div>
      <Field label="Chief complaints (one per line)">
        <textarea className="input" rows={2} disabled={locked} value={lines(record.chief_complaints)} onChange={(e) => set({ chief_complaints: unlines(e.target.value) })} />
      </Field>
      <div className="grid grid-cols-3 gap-3">
        {VITALS.map((k) => (
          <Field key={k} label={k}>
            <input className="input" disabled={locked} value={record.vitals[k]} onChange={(e) => set({ vitals: { ...record.vitals, [k]: e.target.value } })} />
          </Field>
        ))}
      </div>
      <Field label="Diagnosis">
        <input className="input" disabled={locked} value={record.diagnosis} onChange={(e) => set({ diagnosis: e.target.value })} />
      </Field>
      <div>
        <span className="label">Prescription</span>
        <div className="space-y-2">
          {record.prescription.map((rx, i) => (
            <div key={i} className="rounded-xl border border-line bg-bg p-3">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {RX_FIELDS.map((k) => (
                  <input key={k} placeholder={k} aria-label={k} className="input" disabled={locked} value={rx[k]} onChange={(e) => setRx(i, k, e.target.value)} />
                ))}
                <button disabled={locked} className="link text-sm text-left" onClick={() => set({ prescription: record.prescription.filter((_, j) => j !== i) })}>Remove</button>
              </div>
            </div>
          ))}
        </div>
        <button disabled={locked} className="link mt-2 text-sm"
          onClick={() => set({ prescription: [...record.prescription, { drug: '', dose: '', frequency: '', timing: '', duration: '' }] })}>
          + Add medicine
        </button>
      </div>
      <Field label="Advice (one per line)">
        <textarea className="input" rows={2} disabled={locked} value={lines(record.advice)} onChange={(e) => set({ advice: unlines(e.target.value) })} />
      </Field>
      <Field label="Follow-up">
        <input className="input" disabled={locked} value={record.follow_up} onChange={(e) => set({ follow_up: e.target.value })} />
      </Field>
    </div>
  )
}
