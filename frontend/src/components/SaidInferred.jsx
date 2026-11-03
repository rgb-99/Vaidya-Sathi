export default function SaidInferred({ record }) {
  if (!record.said.length && !record.inferred.length) return null
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-xl border border-line bg-white p-3">
        <div className="eyebrow mb-2">Said (quote found in transcript)</div>
        <ul className="space-y-2 text-sm">
          {record.said.map((fact) => {
            const q = record.provenance[fact.split(':')[0]]?.quote
            return <li key={fact}><div className="font-medium">{fact}</div>{q && <div className="italic text-muted">“{q}”</div>}</li>
          })}
        </ul>
      </div>
      <div className="rounded-xl border border-dashed border-amber-400 bg-amber-50 p-3">
        <div className="eyebrow mb-2">AI-suggested, not verified</div>
        {record.inferred.length ? (
          <ul className="space-y-1 text-sm">{record.inferred.map((x) => <li key={x}>{x}</li>)}</ul>
        ) : <p className="text-sm text-muted">Nothing unverified.</p>}
      </div>
    </div>
  )
}
