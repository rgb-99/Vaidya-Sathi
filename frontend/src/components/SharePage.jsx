import { useEffect, useState } from 'react'

const SLOTS = [['morning', 'Morning', '🌅'], ['afternoon', 'Afternoon', '☀️'], ['night', 'Evening / Night', '🌙']]
const wav = (b64) => `data:audio/wav;base64,${b64}`

// Public patient page: no login, large print, phone first. Reached at /share/<token>.
export default function SharePage({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    fetch(`/api/share/${token}`).then(async (r) => (r.ok ? setData(await r.json()) : setError((await r.json()).error)))
      .catch(() => setError('Cannot reach the server.'))
    return () => meta.remove()
  }, [token])

  if (error) return <main className="mx-auto max-w-xl p-6 text-xl" role="alert">{error}</main>
  if (!data) return <main className="mx-auto max-w-xl p-6 text-xl text-muted">Loading…</main>
  const other = data.schedule.other || []
  return (
    <main className="mx-auto max-w-xl space-y-6 p-5 text-xl">
      <h1 className="text-3xl font-bold">{data.first_name ? `${data.first_name}, your medicines` : 'Your medicines'}</h1>
      {data.audio_base64 && (
        <div className="space-y-2">
          <audio id="share-audio" controls src={wav(data.audio_base64)} className="w-full" />
          <button className="btn-accent w-full py-4 text-lg" onClick={() => { const a = document.getElementById('share-audio'); a.currentTime = 0; a.play() }}>Play again</button>
        </div>
      )}
      {SLOTS.map(([key, label, icon]) => (
        <section key={key} className="rounded-2xl border-2 border-ink p-4">
          <h2 className="text-2xl font-semibold">{icon} {label}</h2>
          {data.schedule[key].length ? data.schedule[key].map((m) => (
            <p key={m.medicine + m.detail} className="mt-2"><b>{m.medicine}</b><br /><span className="text-lg text-muted">{m.detail}</span></p>
          )) : <p className="mt-2 text-muted">Nothing</p>}
        </section>
      ))}
      {other.length > 0 && (
        <section className="rounded-2xl border-2 border-ink p-4">
          <h2 className="text-2xl font-semibold">As the doctor told you</h2>
          {other.map((m) => <p key={m.medicine} className="mt-2"><b>{m.medicine}</b><br /><span className="text-lg text-muted">{m.detail}</span></p>)}
        </section>
      )}
      {data.advice.length > 0 && <section><h2 className="text-2xl font-semibold">Advice</h2><ul className="list-disc pl-6">{data.advice.map((a) => <li key={a}>{a}</li>)}</ul></section>}
      {data.follow_up && <section><h2 className="text-2xl font-semibold">Come back</h2><p>{data.follow_up}</p></section>}
      {data.diagnosis && <section><h2 className="text-2xl font-semibold">What the doctor found</h2><p>{data.diagnosis}</p></section>}
      <p className="font-semibold">If you feel worse, go to the hospital immediately.</p>
      <p className="text-sm text-muted">This link expires on {new Date(data.expires_at).toLocaleDateString()}. AI-assisted documentation reviewed by your clinician. Not a substitute for medical judgement.</p>
    </main>
  )
}
