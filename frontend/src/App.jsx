import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import DemoPicker from './components/DemoPicker.jsx'
import Recorder from './components/Recorder.jsx'
import RecordForm from './components/RecordForm.jsx'
import RedFlagBanner from './components/RedFlagBanner.jsx'
import DiarizedTranscript from './components/DiarizedTranscript.jsx'
import EvalPage from './components/EvalPage.jsx'
import History from './components/History.jsx'
import PrescriptionPhoto from './components/PrescriptionPhoto.jsx'
import SafetyWarnings from './components/SafetyWarnings.jsx'
import SaidInferred from './components/SaidInferred.jsx'
import SignOff from './components/SignOff.jsx'
import SummaryPlayer from './components/SummaryPlayer.jsx'

const FALLBACK_LANGS = [{ code: 'mr-IN', name: 'Marathi' }, { code: 'hi-IN', name: 'Hindi' }, { code: 'en-IN', name: 'English' }]
const wavSrc = (b64) => `data:audio/wav;base64,${b64}`

export default function App() {
  const [mock, setMock] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenarioId, setScenarioId] = useState('')
  const [lang, setLang] = useState('mr-IN')
  const [langs, setLangs] = useState(FALLBACK_LANGS)
  const langManual = useRef(false)
  const [utterances, setUtterances] = useState([])
  const [transcript, setTranscript] = useState('')
  const [record, setRecord] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [recordId, setRecordId] = useState(null)
  const [view, setView] = useState('consult')
  const [shareInfo, setShareInfo] = useState(null)
  const [vision, setVision] = useState(false)
  const [includeDx, setIncludeDx] = useState(false)
  const [summary, setSummary] = useState(null)
  const [alertSrc, setAlertSrc] = useState('')
  const [ticket, setTicket] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const flagTimer = useRef(null)

  useEffect(() => {
    api.health().then((h) => setMock(h.mock)).catch((e) => setError(e.message))
    api.features().then((f) => setVision(f.vision)).catch(() => {})
    api.getLanguages().then((l) => l.length && setLangs(l)).catch(() => {})
    api.getScenarios().then(setScenarios).catch((e) => setError(e.message))
  }, [])

  // Apply a /transcribe result: text, speaker turns, and the detected language unless the user chose one.
  const applyTranscript = (r) => {
    setTranscript(r.transcript)
    setUtterances(r.utterances || [])
    if (r.notice) setError(r.notice)
    else if (!r.transcript.trim()) setError('No speech was detected. Try again, or type the transcript manually.')
    if (!langManual.current && langs.some((l) => l.code === r.language)) setLang(r.language)
  }

  const run = async (name, fn) => {
    setBusy(name)
    setError('')
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  // Picking a demo scenario sends its prerecorded clip through the real pipeline (STT is canned in mock mode).
  const pickScenario = async (id) => {
    setScenarioId(id)
    setTranscript(''); setUtterances([])
    setRecord(null); setConfirmed(false); setRecordId(null); setSummary(null); setAlertSrc(''); setTicket(null); setShareInfo(null)
    const s = scenarios.find((x) => x.id === id)
    if (!s) return
    if (!s.audio_url) return setTranscript(s.transcript)
    await run('transcribe', async () => {
      const clip = await fetch(s.audio_url)
      if (!clip.ok) throw new Error('Could not load the demo clip.')
      applyTranscript(await api.transcribe(await clip.blob(), `${id}.wav`))
    })
  }

  const onAudio = (blob, filename) =>
    run('transcribe', async () => {
      applyTranscript(await api.transcribe(blob, filename))
    })

  const extract = () =>
    run('structure', async () => {
      const r = await api.structure(transcript, utterances)
      setRecord(r)
      if (r.warnings?.length) setError(r.warnings[0])
      setConfirmed(false); setRecordId(null); setSummary(null); setTicket(null)
    })

  // Editing vitals re-runs the red-flag rules (debounced).
  const onRecordChange = (next) => {
    setRecord(next)
    clearTimeout(flagTimer.current)
    flagTimer.current = setTimeout(() => {
      api.redflags(next).then((r) => setRecord((cur) => cur && { ...cur, red_flags: r.red_flags })).catch((e) => setError(e.message))
      api.safety(next).then((r) => setRecord((cur) => cur && { ...cur, safety_warnings: r.safety_warnings })).catch(() => {})
    }, 400)
  }

  const genSummary = () => run('summary', async () => setSummary(await api.summary(record, lang)))
  const playAlert = () => run('alert', async () => {
    const r = await api.alertAudio(record.red_flags, lang)
    setAlertSrc(wavSrc(r.audio_base64))
  })
  const signOff = (name) => run('signoff', async () => {
    const r = await api.signoff(record, name)
    setRecord(r.record)
    setRecordId(r.id)
    setConfirmed(true)
  })
  const makeShare = () => run('share', async () => setShareInfo(await api.share(record, lang, includeDx)))
  const makeTicket = () => run('referral', async () => setTicket(await api.referral(record, recordId)))
  const printCard = () => run('card', async () => {
    const html = await api.getCardHtml(record)
    const w = window.open('', '_blank')
    if (!w) throw new Error('Allow pop-ups to print the card.')
    w.document.write(html)
    w.document.close()
    setTimeout(() => w.print(), 300)
  })

  const urgent = record?.red_flags.some((f) => f.severity === 'urgent')

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-5 py-4">
          <h1 className="text-xl font-semibold tracking-tight">Vaidya Saathi</h1>
          {mock && <span className="rounded-full bg-orange-100 px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider text-orange-800">mock mode</span>}
          <nav className="flex gap-1 text-sm">
            {[['consult', 'Consultation'], ['history', 'History'], ['eval', 'Eval']].map(([v, label]) => (
              <button key={v} onClick={() => setView(v)} className={`rounded-full px-3 py-1.5 ${view === v ? 'bg-ink text-white' : 'text-muted hover:text-ink'}`}>{label}</button>
            ))}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select aria-label="Language" className="rounded-full border border-line bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30" value={lang} onChange={(e) => { langManual.current = true; setLang(e.target.value) }}>
              {langs.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
            <DemoPicker scenarios={scenarios} value={scenarioId} onChange={pickScenario} />
          </div>
        </div>
        <p className="bg-ink px-5 py-2 text-center text-sm font-medium text-white">
          AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.
        </p>
      </header>

      {error && (
        <div className="flex items-center justify-center gap-3 border-b border-red-200 bg-red-50 px-5 py-2 text-sm text-red-900" role="alert">
          <span>{error}</span>
          <button className="link" onClick={() => setError('')}>Dismiss</button>
        </div>
      )}

      {view === 'history' ? <History /> : view === 'eval' ? <EvalPage /> : (
      <main className="mx-auto grid max-w-7xl gap-5 px-5 py-6 md:grid-cols-3">
        <section className="card space-y-4">
          <div className="eyebrow">01 — Record</div>
          <Recorder scenarioId={scenarioId} onAudio={onAudio} busy={busy === 'transcribe'} />
          <div>
            <span className="label">Transcript (editable)</span>
            <textarea className="input h-56" placeholder="Transcript appears here"
              value={transcript} onChange={(e) => { setTranscript(e.target.value); setUtterances([]) }} />
          </div>
          <DiarizedTranscript utterances={utterances} onSwap={() => setUtterances((us) => us.map((u) => ({ ...u, speaker: u.speaker === 'clinician' ? 'patient' : u.speaker === 'patient' ? 'clinician' : 'unknown' })))} />
          <button disabled={!transcript || busy === 'structure'} onClick={extract} className="btn-ink w-full">
            {busy === 'structure' ? 'Extracting…' : 'Extract record'}
          </button>
        </section>

        <section className="card space-y-4">
          <div className="eyebrow">02 — Review</div>
          {record ? (
            <>
              <RedFlagBanner flags={record.red_flags} onPlay={playAlert} />
              <SafetyWarnings warnings={record.safety_warnings} />
              {alertSrc && <audio controls autoPlay src={alertSrc} className="w-full" />}
              <RecordForm record={record} onChange={onRecordChange} locked={confirmed} />
              {vision && <PrescriptionPhoto record={record} />}
              <SaidInferred record={record} />
              <SignOff record={record} onSign={signOff} busy={busy === 'signoff'} />
            </>
          ) : <p className="text-sm text-muted">Extract a record from the transcript to begin.</p>}
        </section>

        <section className="card space-y-4">
          <div className="eyebrow">03 — Patient summary</div>
          <SummaryPlayer summary={summary} audioSrc={summary?.audio_base64 ? wavSrc(summary.audio_base64) : ''}
            canGenerate={confirmed} onGenerate={genSummary} busy={busy === 'summary'}>
            {confirmed && (
              <div className="space-y-2 rounded-xl border border-line bg-bg p-3">
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={includeDx} onChange={(e) => setIncludeDx(e.target.checked)} /> Include diagnosis on the patient page</label>
                <button disabled={busy === 'share'} onClick={makeShare} className="btn-ink w-full">{busy === 'share' ? 'Creating…' : 'Create patient share link'}</button>
                {shareInfo && (
                  <div className="space-y-2 text-sm">
                    <img alt="QR code for the patient page" className="mx-auto h-40 w-40" src={`data:image/png;base64,${shareInfo.qr_png_base64}`} />
                    <a className="link break-all" href={shareInfo.url} target="_blank" rel="noreferrer">{shareInfo.url}</a>
                    <div className="text-muted">Expires {new Date(shareInfo.expires_at).toLocaleDateString()}</div>
                  </div>
                )}
                <a className="link block text-sm" href={`/api/schedule.ics?record_id=${recordId}`}>Download reminder calendar (.ics)</a>
              </div>
            )}
            {confirmed && <a className="btn-outline w-full" href={`/api/export/${recordId}.json`} target="_blank" rel="noreferrer">Export (FHIR-inspired JSON)</a>}
            {confirmed && <button disabled={busy === 'card'} onClick={printCard} className="btn-outline w-full">Print medicine card</button>}
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
      )}
    </div>
  )
}
