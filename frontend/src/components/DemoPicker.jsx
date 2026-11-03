export default function DemoPicker({ scenarios, value, onChange }) {
  return (
    <select
      aria-label="Demo scenario"
      className="rounded-full border border-line bg-surface px-4 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">Demo scenario…</option>
      {scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
    </select>
  )
}
