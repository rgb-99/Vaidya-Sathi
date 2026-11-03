import Icon from './Icon.jsx'

const VITALS = [['bp', 'BP'], ['temp', 'Temp °F'], ['pulse', 'Pulse'], ['spo2', 'SpO2'], ['resp_rate', 'Breaths/min'], ['sugar', 'Sugar']]
const RX = [['dose', 'Dose'], ['frequency', 'How often'], ['timing', 'When'], ['duration', 'How long']]

const Field = ({ label, children, className = '' }) => (
  <label className={`block ${className}`}><span className="label">{label}</span>{children}</label>
)

const Section = ({ icon, title, action, children }) => (
  <section className="card space-y-3 p-4 sm:p-5">
    <div className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 place-items-center rounded-full bg-accent-soft"><Icon name={icon} className="h-4 w-4" /></span>
      <h3 className="font-semibold">{title}</h3>
      {action && <div className="ml-auto">{action}</div>}
    </div>
    {children}
  </section>
)

// The record in plain sections. Edits re-run the red-flag and safety rules (see App.jsx).
export default function RecordForm({ record, onChange, locked }) {
  const set = (patch) => onChange({ ...record, ...patch })
  const setRx = (i, k, v) => set({ prescription: record.prescription.map((r, j) => (j === i ? { ...r, [k]: v } : r)) })
  const lines = (arr) => arr.join('\n')
  const unlines = (s) => s.split('\n').filter((x) => x.trim())
  const t = (value, onChangeFn, extra = {}) => <input className="input" disabled={locked} value={value} onChange={(e) => onChangeFn(e.target.value)} {...extra} />

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Section icon="user" title="Patient">
        <div className="grid grid-cols-6 gap-2">
          <Field label="Name" className="col-span-6 sm:col-span-4">{t(record.patient.name, (v) => set({ patient: { ...record.patient, name: v } }))}</Field>
          <Field label="Age" className="col-span-3 sm:col-span-1">{t(record.patient.age, (v) => set({ patient: { ...record.patient, age: v } }))}</Field>
          <Field label="Sex" className="col-span-3 sm:col-span-1">{t(record.patient.sex, (v) => set({ patient: { ...record.patient, sex: v } }))}</Field>
          <Field label="Diagnosis" className="col-span-6">{t(record.diagnosis, (v) => set({ diagnosis: v }))}</Field>
        </div>
      </Section>

      <Section icon="pulse" title="Vitals">
        <div className="grid grid-cols-3 gap-2">
          {VITALS.map(([k, label]) => (
            <label key={k} className="rounded-2xl bg-bg p-2.5">
              <span className="block text-[11px] font-medium uppercase tracking-wide text-muted">{label}</span>
              <input className="w-full bg-transparent text-lg font-semibold tabular-nums text-ink placeholder:text-muted/50 focus:outline-none disabled:opacity-70"
                disabled={locked} placeholder="—" value={record.vitals[k]} onChange={(e) => set({ vitals: { ...record.vitals, [k]: e.target.value } })} />
            </label>
          ))}
        </div>
      </Section>

      <div className="lg:col-span-2">
        <Section icon="pill" title={`Medicines (${record.prescription.length})`} action={
          <button disabled={locked} className="chip px-3 py-1.5 text-xs"
            onClick={() => set({ prescription: [...record.prescription, { drug: '', dose: '', frequency: '', timing: '', duration: '' }] })}>
            <Icon name="plus" className="h-3.5 w-3.5" /> Add medicine
          </button>}>
          <div className="space-y-2">
            {record.prescription.map((rx, i) => (
              <div key={i} className="grid grid-cols-2 items-end gap-2 rounded-2xl bg-bg p-3 sm:grid-cols-[1.6fr_0.8fr_1fr_1.2fr_0.9fr_auto]">
                <Field label="Medicine" className="col-span-2 sm:col-span-1">
                  <input className="input bg-surface font-semibold" disabled={locked} value={rx.drug} onChange={(e) => setRx(i, 'drug', e.target.value)} />
                </Field>
                {RX.map(([k, label]) => (
                  <Field key={k} label={label}>
                    <input className="input bg-surface" disabled={locked} value={rx[k]} onChange={(e) => setRx(i, k, e.target.value)} />
                  </Field>
                ))}
                <button disabled={locked} aria-label="Remove medicine" title="Remove"
                  className="icon-btn col-span-2 w-full text-muted hover:text-red-600 disabled:opacity-40 sm:col-span-1 sm:w-10"
                  onClick={() => set({ prescription: record.prescription.filter((_, j) => j !== i) })}><Icon name="x" className="h-4 w-4" /></button>
              </div>
            ))}
            {!record.prescription.length && <p className="rounded-2xl bg-bg p-4 text-center text-sm text-muted">No medicines in this record.</p>}
          </div>
        </Section>
      </div>

      <Section icon="chat" title="Complaints">
        <textarea className="input" rows={3} disabled={locked} placeholder="One per line" value={lines(record.chief_complaints)} onChange={(e) => set({ chief_complaints: unlines(e.target.value) })} />
      </Section>

      <Section icon="info" title="Advice">
        <textarea className="input" rows={3} disabled={locked} placeholder="One per line" value={lines(record.advice)} onChange={(e) => set({ advice: unlines(e.target.value) })} />
      </Section>

      <Section icon="shield" title="Allergies">
        <textarea className="input" rows={2} disabled={locked} placeholder="One per line. Checked against the medicines." value={lines(record.allergies)} onChange={(e) => set({ allergies: unlines(e.target.value) })} />
      </Section>

      <Section icon="calendar" title="Come back">
        {t(record.follow_up, (v) => set({ follow_up: v }), { placeholder: 'e.g. after 5 days' })}
      </Section>
    </div>
  )
}
