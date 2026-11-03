const VITALS = ['bp', 'temp', 'spo2', 'pulse', 'resp_rate', 'sugar']
const RX_FIELDS = ['drug', 'dose', 'frequency', 'timing', 'duration']
const input = 'border rounded px-2 py-1 w-full disabled:bg-gray-100'

const Field = ({ label, children }) => (
  <label className="block text-sm"><span className="font-semibold">{label}</span>{children}</label>
)

export default function RecordForm({ record, onChange, locked }) {
  const set = (patch) => onChange({ ...record, ...patch })
  const setRx = (i, k, v) => set({ prescription: record.prescription.map((r, j) => (j === i ? { ...r, [k]: v } : r)) })
  const lines = (arr) => arr.join('\n')
  const unlines = (s) => s.split('\n').filter((x) => x.trim())

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {['name', 'age', 'sex'].map((k) => (
          <Field key={k} label={`Patient ${k}`}>
            <input className={input} disabled={locked} value={record.patient[k]} onChange={(e) => set({ patient: { ...record.patient, [k]: e.target.value } })} />
          </Field>
        ))}
      </div>
      <Field label="Chief complaints (one per line)">
        <textarea className={input} rows={2} disabled={locked} value={lines(record.chief_complaints)} onChange={(e) => set({ chief_complaints: unlines(e.target.value) })} />
      </Field>
      <div className="grid grid-cols-3 gap-2">
        {VITALS.map((k) => (
          <Field key={k} label={k}>
            <input className={input} disabled={locked} value={record.vitals[k]} onChange={(e) => set({ vitals: { ...record.vitals, [k]: e.target.value } })} />
          </Field>
        ))}
      </div>
      <Field label="Diagnosis">
        <input className={input} disabled={locked} value={record.diagnosis} onChange={(e) => set({ diagnosis: e.target.value })} />
      </Field>
      <div>
        <div className="font-semibold text-sm">Prescription</div>
        {record.prescription.map((rx, i) => (
          <div key={i} className="grid grid-cols-6 gap-1 mb-1">
            {RX_FIELDS.map((k) => (
              <input key={k} placeholder={k} className={input} disabled={locked} value={rx[k]} onChange={(e) => setRx(i, k, e.target.value)} />
            ))}
            <button disabled={locked} className="text-red-700 disabled:opacity-40" onClick={() => set({ prescription: record.prescription.filter((_, j) => j !== i) })}>Remove</button>
          </div>
        ))}
        <button disabled={locked} className="text-blue-700 text-sm disabled:opacity-40"
          onClick={() => set({ prescription: [...record.prescription, { drug: '', dose: '', frequency: '', timing: '', duration: '' }] })}>
          + Add medicine
        </button>
      </div>
      <Field label="Advice (one per line)">
        <textarea className={input} rows={2} disabled={locked} value={lines(record.advice)} onChange={(e) => set({ advice: unlines(e.target.value) })} />
      </Field>
      <Field label="Follow-up">
        <input className={input} disabled={locked} value={record.follow_up} onChange={(e) => set({ follow_up: e.target.value })} />
      </Field>
    </div>
  )
}
