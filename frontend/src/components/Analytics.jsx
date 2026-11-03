import { useEffect, useState } from 'react'

const show = (v, unit = '') => (v === null || v === undefined ? 'not measured' : `${v}${unit}`)

export default function Analytics() {
  const [data, setData] = useState(null)
  const [baseline, setBaseline] = useState('')
  const [error, setError] = useState('')
  const load = () => fetch('/api/analytics').then((r) => r.json()).then(setData).catch(() => setError('Cannot reach the server.'))
  useEffect(() => { load() }, [])
  const save = async () => {
    setError('')
    const res = await fetch('/api/analytics/baseline', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ minutes: Number(baseline) }) })
    const body = await res.json()
    if (!res.ok) return setError(body.error)
    setData(body)
  }
  if (!data) return <main className="mx-auto max-w-3xl px-5 py-6 text-muted">{error || 'Loading…'}</main>
  const rows = [
    ['Consultations signed off', `${data.consultations} (${data.live_consultations} live, ${data.demo_consultations} demo)`],
    ['Live consultations with a measured time', data.timed_consultations],
    ['Mean documentation time (transcript ready to sign-off)', show(data.mean_documentation_minutes, ' min')],
    ['Your typing baseline', show(data.baseline_minutes, ' min')],
    ['Mean minutes saved per consultation', show(data.mean_minutes_saved, ' min')],
    ['Total minutes saved', show(data.total_minutes_saved, ' min')],
    ['Red flags raised (urgent)', `${data.red_flags} (${data.urgent_red_flags})`],
    ['Prescription safety warnings', data.safety_warnings],
    ['Language mix', Object.entries(data.language_mix).map(([k, v]) => `${k}: ${v}`).join(', ') || 'none yet'],
  ]
  return (
    <main className="mx-auto max-w-3xl space-y-5 px-5 py-6">
      <section className="card space-y-3">
        <div className="eyebrow">Typing baseline (enter once)</div>
        <div className="flex gap-2">
          <input className="input max-w-[10rem]" type="number" min="1" max="120" placeholder="minutes" value={baseline} onChange={(e) => setBaseline(e.target.value)} />
          <button className="btn-ink" disabled={!baseline} onClick={save}>Save</button>
        </div>
        <p className="text-xs text-muted">How many minutes you normally spend typing one record by hand. Without it, no minutes-saved figure is shown.</p>
        {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
      </section>
      <section className="card">
        <table className="w-full text-sm"><tbody>
          {rows.map(([k, v]) => <tr key={k} className="border-t border-line first:border-0"><td className="py-2 text-muted">{k}</td><td className="py-2 text-right font-mono">{v}</td></tr>)}
        </tbody></table>
        <p className="mt-3 text-xs text-muted">{data.note}</p>
      </section>
    </main>
  )
}
