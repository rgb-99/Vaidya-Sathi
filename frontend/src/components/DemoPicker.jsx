export default function DemoPicker({ scenarios, value, onChange }) {
  return (
    <select className="border rounded px-2 py-1 text-black" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Pick demo scenario…</option>
      {scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
    </select>
  )
}
