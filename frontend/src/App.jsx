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

  const onTranscribe = (blob, filename) =>
    run('transcribe', async () => {
      const r = await api.transcribe(blob, filename)
      setTranscript(r.transcript)
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
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-blue-900 text-white p-3 space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold">Vaidya Saathi</h1>
          {mock && <span className="bg-yellow-400 text-black text-xs font-bold px-2 py-0.5 rounded">MOCK MODE</span>}
          <select className="text-black rounded px-2 py-1 ml-auto" value={lang} onChange={(e) => setLang(e.target.value)}>
            {LANGS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
          </select>
          <DemoPicker scenarios={scenarios} value={scenarioId} onChange={pickScenario} />
        </div>
        <p className="text-sm font-semibold">AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.</p>
      </header>

      {error && <div className="bg-red-100 text-red-900 p-2 text-center" role="alert">{error}</div>}

      <main className="grid gap-4 p-4 md:grid-cols-3">
        <section className="space-y-3">
          <h2 className="font-bold">1. Recorder and transcript</h2>
          <Recorder scenarioId={scenarioId} onTranscribe={onTranscribe} busy={busy === 'transcribe'} />
          {busy === 'transcribe' && <p>Transcribing…</p>}
          <textarea className="border rounded w-full p-2 h-56" placeholder="Transcript appears here (editable)"
            value={transcript} onChange={(e) => setTranscript(e.target.value)} />
          <button disabled={!transcript || busy === 'structure'} onClick={extract} className="w-full bg-blue-700 text-white rounded py-2 disabled:opacity-40">
            {busy === 'structure' ? 'Extracting…' : 'Extract record'}
          </button>
        </section>

        <section className="space-y-3">
          <h2 className="font-bold">2. Clinical record</h2>
          {record ? (
            <>
              <RedFlagBanner flags={record.red_flags} onPlay={playAlert} />
              {alertSrc && <audio controls autoPlay src={alertSrc} className="w-full" />}
              <RecordForm record={record} onChange={onRecordChange} locked={confirmed} />
              <button disabled={confirmed} onClick={() => setConfirmed(true)} className="w-full bg-green-700 text-white rounded py-2 disabled:opacity-60">
                {confirmed ? 'Record confirmed' : 'Confirm record'}
              </button>
            </>
          ) : <p className="text-gray-500">Extract a record from the transcript to begin.</p>}
        </section>

        <section className="space-y-3">
          <h2 className="font-bold">3. Patient summary</h2>
          <SummaryPlayer summary={summary} audioSrc={summary && wavSrc(summary.audio_base64)}
            canGenerate={confirmed} onGenerate={genSummary} busy={busy === 'summary'}>
            {confirmed && urgent && (
              <div className="border rounded p-3 bg-white space-y-2">
                <button disabled={busy === 'referral'} onClick={makeTicket} className="bg-red-700 text-white rounded px-3 py-2">Create referral ticket</button>
                {ticket && (
                  <div className="text-sm">
                    <div className="font-bold">Ticket {ticket.ticket_id}</div>
                    <div>To: {ticket.destination}</div>
                    <div>{new Date(ticket.created_at).toLocaleString()}</div>
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
