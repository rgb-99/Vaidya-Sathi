import { useEffect, useState } from 'react'
import * as api from '../api.js'

export default function History() {
  const [records, setRecords] = useState([])
  const [tickets, setTickets] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getRecords(), api.getTickets()]).then(([r, t]) => { setRecords(r); setTickets(t) }).catch((e) => setError(e.message))
  }, [])

  const when = (iso) => new Date(iso).toLocaleString()
  return (
    <main className="grid w-full gap-3 p-3 md:grid-cols-2">
      {error && <p className="text-red-700 dark:text-red-300 dark:text-red-300" role="alert">{error}</p>}
      <section className="card space-y-3">
        <div className="eyebrow">Confirmed records</div>
        {!records.length && <p className="text-sm text-muted">No confirmed records yet.</p>}
        {records.map(({ id, created_at, record }) => (
          <div key={id} className="rounded-xl border border-line bg-bg p-3 text-sm">
            <div className="font-semibold">#{id} <span className="font-normal text-muted">{when(created_at)}</span></div>
            <div>{record.chief_complaints.join(', ') || 'No complaints recorded'}</div>
            <div className="text-muted">{record.prescription.map((r) => `${r.drug} ${r.dose}`.trim()).join('; ') || 'No medicines'}</div>
          </div>
        ))}
      </section>
      <section className="card space-y-3">
        <div className="eyebrow">Referral tickets</div>
        {!tickets.length && <p className="text-sm text-muted">No tickets yet.</p>}
        {tickets.map((t) => (
          <div key={t.ticket_id} className="rounded-xl border border-line bg-bg p-3 text-sm">
            <div className="font-semibold">{t.ticket_id} <span className="font-normal text-muted">{when(t.created_at)}</span></div>
            <div>To: {t.payload.destination}</div>
            <div className="text-muted">{t.payload.red_flags.map((f) => f.title).join(', ') || 'No red flags'}</div>
          </div>
        ))}
      </section>
    </main>
  )
}
