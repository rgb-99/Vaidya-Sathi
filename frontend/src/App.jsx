import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import DemoPicker from './components/DemoPicker.jsx'
import Recorder from './components/Recorder.jsx'
import RecordForm from './components/RecordForm.jsx'
import RedFlagBanner from './components/RedFlagBanner.jsx'
import DiarizedTranscript from './components/DiarizedTranscript.jsx'
import Analytics from './components/Analytics.jsx'
import EvalPage from './components/EvalPage.jsx'
import History from './components/History.jsx'
import OfflineQueue from './components/OfflineQueue.jsx'
import { enqueue } from './offline.js'
import PrescriptionPhoto from './components/PrescriptionPhoto.jsx'
import SafetyWarnings from './components/SafetyWarnings.jsx'
import SaidInferred from './components/SaidInferred.jsx'
import SignOff from './components/SignOff.jsx'
import SummaryPlayer from './components/SummaryPlayer.jsx'

const FALLBACK_LANGS = [{ code: 'mr-IN', name: 'Marathi' }, { code: 'hi-IN', name: 'Hindi' }, { code: 'en-IN', name: 'English' }]
const FALLBACK_LANG = 'en-IN'   // only when no language could be detected at all; never an assumed regional language
const wavSrc = (b64) => `data:audio/wav;base64,${b64}`

export default function App() {
  const [mock, setMock] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenarioId, setScenarioId] = useState('')
  const [langChoice, setLangChoice] = useState('auto')   // 'auto' = follow the detected language, or a language code picked by hand
  const [detected, setDetected] = useState('')
  const [langs, setLangs] = useState(FALLBACK_LANGS)
  const [tab, setTab] = useState('record')
  const [theme, setTheme] = useState(() => (document.documentElement.classList.contains('dark') ? 'dark' : 'light'))
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.toggle('dark', next === 'dark')
    try { localStorage.setItem('vs-theme', next) } catch { /* private window: the choice just is not remembered */ }
    setTheme(next)
  }
  // Language used for the summary, alerts and share page. Auto: the language heard in the audio (or named in the
  // record); a language without a voice falls back to English, and so does a run where nothing could be detected.
  const supported = (code) => langs.some((l) => l.code === code)
  const lang = langChoice !== 'auto' ? langChoice : detected ? (supported(detected) ? detected : FALLBACK_LANG) : FALLBACK_LANG
  const langName = (code) => langs.find((l) => l.code === code)?.name || code
  const [utterances, setUtterances] = useState([])
  const [transcript, setTranscript] = useState('')
  const [record, setRecord] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [recordId, setRecordId] = useState(null)
  const [view, setView] = useState('consult')
  const [shareInfo, setShareInfo] = useState(null)
  const [vision, setVision] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const live = useRef({ text: '', timer: null })
  const startedAt = useRef('')   // when the transcript became available: the start of the measured documentation time
  const markStart = () => { if (!startedAt.current) startedAt.current = new Date().toISOString() }
  const [includeDx, setIncludeDx] = useState(false)
  const [summary, setSummary] = useState(null)
  const [alertSrc, setAlertSrc] = useState('')
  const [ticket, setTicket] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const flagTimer = useRef(null)

  useEffect(() => {
    api.health().then((h) => setMock(h.mock)).catch((e) => setError(e.message))
    api.features().then((f) => { setVision(f.vision); setStreaming(f.streaming) }).catch(() => {})
    api.getLanguages().then((l) => l.length && setLangs(l)).catch(() => {})
    api.getScenarios().then(setScenarios).catch((e) => setError(e.message))
  }, [])

  // Apply a /transcribe result: text, speaker turns, and the detected language unless the user chose one.
  const applyTranscript = (r) => {
    if (r.transcript?.trim()) markStart()
    setTranscript(r.transcript)
    setUtterances(r.utterances || [])
    if (r.notice) setError(r.notice)
    else if (!r.transcript.trim()) setError('No speech was detected. Try again, or type the transcript manually.')
    if (r.language) setDetected(r.language)
  }

  // Live mode: words are appended as they arrive, and the form is re-filled every few seconds (debounced).
  const livePartial = (text) => {
    markStart()
    live.current.text = `${live.current.text} ${text}`.trim()
    setTranscript(live.current.text)
    setUtterances([])
    if (!live.current.timer) {
      live.current.timer = setTimeout(async () => {
        live.current.timer = null
        try { setRecord(await api.structure(live.current.text)) } catch { /* the final extraction reports errors */ }
      }, 4000)
    }
  }
  const liveDone = (full) => {
    clearTimeout(live.current.timer)
    live.current = { text: '', timer: null }
    setTranscript(full)
    setConfirmed(false); setRecordId(null)
    run('structure', async () => {
      const r = await api.structure(full)
      setRecord(r)
      if (/^[a-z]{2,3}-IN$/.test(r.language_detected || '')) setDetected((d) => d || r.language_detected)
    })
  }

  const run = async (name, fn) => {
    setBusy(name)
    setError('')
    try { await fn() } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  // Picking a demo scenario sends its prerecorded clip through the real pipeline (STT is canned in mock mode).
  const pickScenario = async (id) => {
    setScenarioId(id)
    startedAt.current = ''
    setTranscript(''); setUtterances([]); setDetected('')
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

  const onAudio = (blob, filename) => {
    if (!navigator.onLine) {   // no network: keep the recording on the device and sync later
      enqueue(blob, filename).then(() => setError('You are offline. The recording is saved and will be transcribed when you are back online.')).catch((e) => setError(e.message))
      return
    }
    return run('transcribe', async () => {
      applyTranscript(await api.transcribe(blob, filename))
    })
  }

  const extract = () =>
    run('structure', async () => {
      const r = await api.structure(transcript, utterances)
      setRecord(r)
      if (/^[a-z]{2,3}-IN$/.test(r.language_detected || '')) setDetected((d) => d || r.language_detected)
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
    const r = await api.signoff(record, name, startedAt.current, Boolean(scenarioId))
    startedAt.current = ''
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
  const tabs = [['record', 'Record'], ['evidence', `Evidence${record?.inferred?.length ? ` (${record.inferred.length} unverified)` : ''}`], ...(vision ? [['photo', 'Prescription photo']] : [])]
  const swap = () => setUtterances((us) => us.map((u) => ({ ...u, speaker: u.speaker === 'clinician' ? 'patient' : u.speaker === 'patient' ? 'clinician' : 'unknown' })))
  const select = 'rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30'

  return (
    <div className="flex min-h-screen flex-col lg:h-screen lg:overflow-hidden">
      <header className="shrink-0 border-b border-line bg-surface">
        <div className="flex flex-wrap items-center gap-3 px-4 py-2">
          <h1 className="text-lg font-semibold tracking-tight">Vaidya Saathi</h1>
          {mock && <span className="rounded-full bg-orange-100 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-orange-800 dark:bg-orange-900/40 dark:text-orange-200">mock mode</span>}
          <nav className="flex gap-1 text-sm">
            {[['consult', 'Consultation'], ['history', 'History'], ['stats', 'Analytics'], ['eval', 'Eval']].map(([v, label]) => (
              <button key={v} onClick={() => setView(v)} className={`rounded-full px-3 py-1 ${view === v ? 'bg-ink text-bg' : 'text-muted hover:text-ink'}`}>{label}</button>
            ))}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select aria-label="Language" title="Language of the summary, alerts and share page" className={select} value={langChoice} onChange={(e) => setLangChoice(e.target.value)}>
              <option value="auto">{`Auto-detect${langChoice === 'auto' && detected ? ` (${langName(detected)})` : ''}`}</option>
              {langs.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
            <DemoPicker scenarios={scenarios} value={scenarioId} onChange={pickScenario} />
            <button className={select} onClick={toggleTheme} aria-label="Switch between dark and light theme" title="Switch theme">{theme === 'dark' ? 'Light' : 'Dark'}</button>
          </div>
        </div>
        <p className="border-t border-amber-300 bg-amber-100 px-4 py-1 text-center text-xs font-medium text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
          AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.
        </p>
      </header>

      {error && (
        <div className="flex shrink-0 items-center justify-center gap-3 border-b border-red-200 bg-red-50 px-4 py-1.5 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200" role="alert">
          <span>{error}</span>
          <button className="link" onClick={() => setError('')}>Dismiss</button>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
      {view === 'history' ? <History /> : view === 'eval' ? <EvalPage /> : view === 'stats' ? <Analytics /> : (
      <main className="grid h-full w-full gap-3 p-3 lg:grid-cols-[minmax(280px,1fr)_minmax(0,2.2fr)_minmax(260px,1fr)]">
        {/* 1. capture */}
        <section className="card flex min-h-0 flex-col gap-3 overflow-hidden">
          <div className="eyebrow">01 · Record</div>
          <Recorder scenarioId={scenarioId} onAudio={onAudio} busy={busy === 'transcribe'} streaming={streaming}
            language={langChoice === 'auto' ? (detected || 'unknown') : langChoice} onLivePartial={livePartial} onLiveDone={liveDone} />
          <div className="flex min-h-[8rem] flex-1 flex-col">
            <span className="label">Transcript (editable)</span>
            <textarea className="input min-h-0 flex-1 resize-none" placeholder="Transcript appears here"
              value={transcript} onChange={(e) => { if (e.target.value.trim()) markStart(); setTranscript(e.target.value); setUtterances([]) }} />
          </div>
          <div className="max-h-40 shrink-0 overflow-y-auto"><DiarizedTranscript utterances={utterances} onSwap={swap} /></div>
          <OfflineQueue onUse={applyTranscript} />
          <button disabled={!transcript || busy === 'structure'} onClick={extract} className="btn-ink w-full shrink-0">
            {busy === 'structure' ? 'Extracting…' : 'Extract record'}
          </button>
        </section>

        {/* 2. review */}
        <section className="card flex min-h-0 flex-col gap-2 overflow-hidden">
          <div className="flex items-center gap-3">
            <div className="eyebrow">02 · Review</div>
            {record && (
              <div className="ml-auto flex gap-1 text-xs">
                {tabs.map(([k, label]) => (
                  <button key={k} onClick={() => setTab(k)} className={`rounded-full px-3 py-1 ${tab === k ? 'bg-ink text-bg' : 'text-muted hover:text-ink'}`}>{label}</button>
                ))}
              </div>
            )}
          </div>
          {record ? (
            <>
              <div className="max-h-[38%] shrink-0 space-y-2 overflow-y-auto empty:hidden">
                <RedFlagBanner flags={record.red_flags} onPlay={playAlert} />
                <SafetyWarnings warnings={record.safety_warnings} />
                {alertSrc && <audio controls autoPlay src={alertSrc} className="h-8 w-full" />}
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                {tab === 'record' && <RecordForm record={record} onChange={onRecordChange} locked={confirmed} />}
                {tab === 'evidence' && <SaidInferred record={record} />}
                {tab === 'photo' && vision && <PrescriptionPhoto record={record} />}
              </div>
              <div className="shrink-0"><SignOff record={record} onSign={signOff} busy={busy === 'signoff'} /></div>
            </>
          ) : <p className="text-sm text-muted">Record or pick a demo scenario, then press “Extract record”.</p>}
        </section>

        {/* 3. patient */}
        <section className="card flex min-h-0 flex-col gap-3 overflow-hidden">
          <div className="eyebrow">03 · Patient{langChoice !== 'auto' ? ` · ${langName(lang)}` : detected ? ` · ${langName(lang)} (auto)` : ' · language auto-detected'}</div>
          <SummaryPlayer summary={summary} audioSrc={summary?.audio_base64 ? wavSrc(summary.audio_base64) : ''}
            canGenerate={confirmed} onGenerate={genSummary} busy={busy === 'summary'}>
            {confirmed && (
              <div className="shrink-0 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <button disabled={busy === 'share'} onClick={makeShare} className="btn-ink">{busy === 'share' ? 'Creating…' : 'Share link + QR'}</button>
                  <button disabled={busy === 'card'} onClick={printCard} className="btn-outline">Print card</button>
                  <a className="btn-outline" href={`/api/schedule.ics?record_id=${recordId}`}>Reminders (.ics)</a>
                  <a className="btn-outline" href={`/api/export/${recordId}.json`} target="_blank" rel="noreferrer">Export JSON</a>
                </div>
                <label className="flex items-center gap-2 text-xs text-muted"><input type="checkbox" checked={includeDx} onChange={(e) => setIncludeDx(e.target.checked)} /> Show diagnosis on the patient page</label>
                {shareInfo && (
                  <div className="flex items-center gap-3 rounded-xl border border-line bg-bg p-2 text-xs">
                    <img alt="QR code for the patient page" className="h-24 w-24 shrink-0 rounded bg-white p-1" src={`data:image/png;base64,${shareInfo.qr_png_base64}`} />
                    <div className="min-w-0">
                      <a className="link break-all" href={shareInfo.url} target="_blank" rel="noreferrer">{shareInfo.url}</a>
                      <div className="text-muted">Expires {new Date(shareInfo.expires_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                )}
                {urgent && (
                  <div className="rounded-xl border border-line bg-bg p-2">
                    <button disabled={busy === 'referral'} onClick={makeTicket} className="btn-danger w-full">Create referral ticket</button>
                    {ticket && <div className="mt-1 text-xs"><b>{ticket.ticket_id}</b> <span className="text-muted">to {ticket.destination}, {new Date(ticket.created_at).toLocaleString()}</span></div>}
                  </div>
                )}
              </div>
            )}
          </SummaryPlayer>
        </section>
      </main>
      )}
      </div>
    </div>
  )
}
