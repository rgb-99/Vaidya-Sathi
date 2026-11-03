import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import DemoPicker from './components/DemoPicker.jsx'
import Recorder from './components/Recorder.jsx'
import RecordForm from './components/RecordForm.jsx'
import RedFlagBanner from './components/RedFlagBanner.jsx'
import SummaryPlayer from './components/SummaryPlayer.jsx'

const LANGS = [['mr-IN', 'Marathi'], ['hi-IN', 'Hindi'], ['en-IN', 'English']]
const wavSrc = (b64) => `data:audio/wav;base64,${b64}`

export default function App() {
  const [mock, setMock] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenarioId, setScenarioId] = useState('')
  const [lang, setLang] = useState('mr-IN')
  const [transcript, setTranscript] = useState('')
  const [record, setRecord] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [summary, setSummary] = useState(null)
  const [alertSrc, setAlertSrc] = useState('')
  const [ticket, setTicket] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const flagTimer = useRef(null)

  useEffect(() => {
    api.health().then((h) => setMock(h.mock)).catch((e) => setError(e.message))
    api.getScenarios().then(setScenarios).catch(() => {})
  }, [])

  const run = async (name, fn) => {
    setBusy(name)
    setError('')
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  const pickScenario = (id) => {
    setScenarioId(id)
    setTranscript(scenarios.find((s) => s.id === id)?.transcript || '')
    setRecord(null); setConfirmed(false); setSummary(null); setAlertSrc(''); setTicket(null)
  }

  const onAudio = (blob, filename) =>
    run('transcribe', async () => {
      const r = await api.transcribe(blob, filename)
      setTranscript(r.transcript)
      if (!r.transcript.trim()) setError('No speech was detected. Try again, or type the transcript manually.')
    })

  const extract = () =>
    run('structure', async () => {
      setRecord(await api.structure(transcript))
      setConfirmed(false); setSummary(null); setTicket(null)
    })

  // Editing vitals re-runs the red-flag rules (debounced).
  const onRecordChange = (next) => {
    setRecord(next)
    clearTimeout(flagTimer.current)
    flagTimer.current = setTimeout(() => {
      api.redflags(next).then((r) => setRecord((cur) => cur && { ...cur, red_flags: r.red_flags })).catch((e) => setError(e.message))
    }, 400)
  }

  const genSummary = () => run('summary', async () => setSummary(await api.summary(record, lang)))
  const playAlert = () => run('alert', async () => {
    const r = await api.alertAudio(record.red_flags, lang)
    setAlertSrc(wavSrc(r.audio_base64))
  })
  const makeTicket = () => run('referral', async () => setTicket(await api.referral(record)))

  const urgent = record?.red_flags.some((f) => f.severity === 'urgent')

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-4">
          <h1 className="text-xl font-semibold tracking-tight">Vaidya Saathi</h1>
          {mock && <span className="rounded-full bg-orange-100 px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider text-orange-800">mock mode</span>}
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select aria-label="Language" className="rounded-full border border-line bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30" value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
            </select>
            <DemoPicker scenarios={scenarios} value={scenarioId} onChange={pickScenario} />
          </div>
        </div>
        <p className="bg-ink px-5 py-2 text-center text-sm font-medium text-white">
          AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.
        </p>
      </header>

      {error && <div className="border-b border-red-200 bg-red-50 px-5 py-2 text-center text-sm text-red-900" role="alert">{error}</div>}

      <main className="mx-auto grid max-w-7xl gap-5 px-5 py-6 md:grid-cols-3">
        <section className="card space-y-4">
          <div className="eyebrow">01 — Record</div>
          <Recorder scenarioId={scenarioId} onAudio={onAudio} busy={busy === 'transcribe'} />
          <div>
            <span className="label">Transcript (editable)</span>
            <textarea className="input h-56" placeholder="Transcript appears here"
              value={transcript} onChange={(e) => setTranscript(e.target.value)} />
          </div>
          <button disabled={!transcript || busy === 'structure'} onClick={extract} className="btn-ink w-full">
            {busy === 'structure' ? 'Extracting…' : 'Extract record'}
          </button>
        </section>

        <section className="card space-y-4">
          <div className="eyebrow">02 — Review</div>
          {record ? (
            <>
              <RedFlagBanner flags={record.red_flags} onPlay={playAlert} />
              {alertSrc && <audio controls autoPlay src={alertSrc} className="w-full" />}
              <RecordForm record={record} onChange={onRecordChange} locked={confirmed} />
              <button disabled={confirmed} onClick={() => setConfirmed(true)} className="btn-ink w-full">
                {confirmed ? 'Record confirmed' : 'Confirm record'}
              </button>
            </>
          ) : <p className="text-sm text-muted">Extract a record from the transcript to begin.</p>}
        </section>

        <section className="card space-y-4">
          <div className="eyebrow">03 — Patient summary</div>
          <SummaryPlayer summary={summary} audioSrc={summary && wavSrc(summary.audio_base64)}
            canGenerate={confirmed} onGenerate={genSummary} busy={busy === 'summary'}>
            {confirmed && urgent && (
              <div className="space-y-3 rounded-xl border border-line bg-bg p-4">
                <button disabled={busy === 'referral'} onClick={makeTicket} className="btn-danger">Create referral ticket</button>
                {ticket && (
                  <div className="text-sm">
                    <div className="font-semibold">Ticket {ticket.ticket_id}</div>
                    <div className="text-muted">To: {ticket.destination}</div>
                    <div className="text-muted">{new Date(ticket.created_at).toLocaleString()}</div>
                  </div>
                )}
              </div>
            )}
          </SummaryPlayer>
        </section>
      </main>
    </div>
  )
}
