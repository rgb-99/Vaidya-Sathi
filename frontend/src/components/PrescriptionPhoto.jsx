import { useRef, useState } from 'react'
import * as api from '../api.js'

const LABEL = { new: 'New today', stopped: 'Not on today\'s prescription', dose_changed: 'Dose changed', unchanged: 'Unchanged' }
const COLOR = { new: 'bg-green-50 border-green-300', stopped: 'bg-red-50 dark:bg-red-950/40 border-red-300', dose_changed: 'bg-amber-50 dark:bg-amber-950/40 border-amber-300', unchanged: 'bg-bg border-line' }

// Reads an older (fake) prescription photo and compares it with today's record. Nothing is merged: each line
// can be marked accepted or rejected by the clinician, which only records their review.
export default function PrescriptionPhoto({ record }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const [lines, setLines] = useState([])
  const [decisions, setDecisions] = useState({})
  const input = useRef(null)

  const upload = async (file) => {
    setBusy(true); setError(''); setItems([]); setLines([]); setDecisions({})
    try {
      const form = new FormData()
      form.append('image', file, file.name)
      const res = await fetch('/api/prescription-photo', { method: 'POST', body: form })
      const start = await res.json()
      if (!res.ok) throw new Error(start.error)
      for (let i = 0; i < 60; i++) {
        const job = await (await fetch(`/api/prescription-photo/${start.job_id}`)).json()
        if (job.status === 'completed') {
          setItems(job.items)
          setLines((await api.reconcile(record, job.items)).lines)
          return
        }
        if (job.status === 'failed') throw new Error(job.error)
        await new Promise((r) => setTimeout(r, 2000))
      }
      throw new Error('Reading the photo took too long.')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2 rounded-xl border border-line bg-bg p-3">
      <div className="label mb-0">Older prescription photo (fake samples only)</div>
      <input ref={input} type="file" accept="image/png,image/jpeg,application/pdf" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) upload(f) }} />
      <button className="btn-outline" disabled={busy} onClick={() => input.current.click()}>{busy ? 'Reading photo…' : 'Upload photo'}</button>
      {error && <p className="text-sm text-red-700 dark:text-red-300 dark:text-red-300" role="alert">{error}</p>}
      {lines.map((l) => (
        <div key={l.drug} className={`rounded-lg border p-2 text-sm ${COLOR[l.status]}`}>
          <div className="font-medium">{l.drug}: {LABEL[l.status]}</div>
          <div className="text-muted">Photo: {l.old_dose || 'not on photo'}, today: {l.new_dose || 'not prescribed'}
            {l.confidence !== null && <span className={l.confidence < 0.7 ? ' font-semibold text-red-700' : ''}> (read confidence {Math.round(l.confidence * 100)}%{l.confidence < 0.7 ? ', check the photo' : ''})</span>}</div>
          <div className="mt-1 flex gap-3">
            {['accepted', 'rejected'].map((d) => (
              <button key={d} className={`link text-xs ${decisions[l.drug] === d ? 'font-bold no-underline' : ''}`} onClick={() => setDecisions({ ...decisions, [l.drug]: d })}>{d === 'accepted' ? 'Accept' : 'Reject'}</button>
            ))}
            {decisions[l.drug] && <span className="text-xs text-muted">{decisions[l.drug]} (prescription not changed)</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
