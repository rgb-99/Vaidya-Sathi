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
import Icon, { Spinner } from './components/Icon.jsx'
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

// The consultation is a three-step flow, one screen per step, one main button per screen.
const STEPS = [[1, 'Record', 'mic'], [2, 'Check', 'clipboard'], [3, 'Patient', 'user']]
const VIEWS = [['consult', 'Consultation', 'mic'], ['history', 'History', 'clock'], ['stats', 'Analytics', 'chart'], ['eval', 'Eval', 'badge']]

function Stepper({ step, done, canReach, onGo, className = '' }) {
  return (
    <ol className={`flex items-center justify-center gap-1.5 sm:gap-2 ${className}`}>
      {STEPS.map(([n, label, icon], i) => {
        const current = n === step
        return (
          <li key={n} className="flex items-center gap-1.5 sm:gap-2">
            {i > 0 && <span className={`h-0.5 w-5 rounded-full sm:w-10 ${canReach(n) ? 'bg-ink/60' : 'bg-line'}`} />}
            <button disabled={!canReach(n)} onClick={() => onGo(n)} aria-current={current ? 'step' : undefined}
              className={`flex items-center gap-2 rounded-full py-1 pl-1 pr-3.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${current ? 'bg-accent text-onaccent' : 'text-muted hover:text-ink'}`}>
              <span className={`grid h-7 w-7 place-items-center rounded-full ${current ? 'bg-onaccent/15' : done[n] ? 'bg-green-600 text-white' : 'bg-accent-soft'}`}>
                {done[n] && !current ? <Icon name="check" className="h-4 w-4" /> : <Icon name={icon} className="h-4 w-4" />}
              </span>
              {label}
            </button>
          </li>
        )
      })}
    </ol>
  )
}

const Heading = ({ title, sub, children }) => (
  <div className="flex flex-wrap items-end gap-3">
    <div className="min-w-0">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {sub && <p className="mt-1 text-muted">{sub}</p>}
    </div>
    {children}
  </div>
)

export default function App() {
  const [mock, setMock] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [scenarioId, setScenarioId] = useState('')
  const [langChoice, setLangChoice] = useState('auto')   // 'auto' = follow the detected language, or a language code picked by hand
  const [detected, setDetected] = useState('')
  const [langs, setLangs] = useState(FALLBACK_LANGS)
  const [step, setStep] = useState(1)
  const [tab, setTab] = useState('record')
  const [menuOpen, setMenuOpen] = useState(false)
  const [typing, setTyping] = useState(false)   // the user chose to type the transcript instead of recording
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
    setStep(2)
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

  // Back to an empty step 1 for the next patient. The language choice is kept.
  const resetConsult = () => {
    startedAt.current = ''
    setScenarioId(''); setTyping(false); setTab('record'); setStep(1)
    setTranscript(''); setUtterances([]); setDetected('')
    setRecord(null); setConfirmed(false); setRecordId(null); setSummary(null); setAlertSrc(''); setTicket(null); setShareInfo(null)
  }

  // Picking a demo scenario sends its prerecorded clip through the real pipeline (STT is canned in mock mode).
  const pickScenario = async (id) => {
    resetConsult()
    setScenarioId(id)
    const s = scenarios.find((x) => x.id === id)
    if (!s) return
    if (!s.audio_url) return setTranscript(s.transcript)
    await run('transcribe', async () => {
      const clip = await fetch(api.apiUrl(s.audio_url))
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

  const extract = () => {
    setStep(2)
    run('structure', async () => {
      const r = await api.structure(transcript, utterances)
      setRecord(r)
      if (/^[a-z]{2,3}-IN$/.test(r.language_detected || '')) setDetected((d) => d || r.language_detected)
      if (r.warnings?.length) setError(r.warnings[0])
      setConfirmed(false); setRecordId(null); setSummary(null); setTicket(null); setShareInfo(null); setAlertSrc('')
    })
  }

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
    setStep(3)
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
  const tabs = [['record', 'Details', 'clipboard'], ['evidence', `Evidence${record?.inferred?.length ? ` (${record.inferred.length} unverified)` : ''}`, 'eye'], ...(vision ? [['photo', 'Old prescription', 'camera']] : [])]
  const swap = () => setUtterances((us) => us.map((u) => ({ ...u, speaker: u.speaker === 'clinician' ? 'patient' : u.speaker === 'patient' ? 'clinician' : 'unknown' })))
  const canReach = (n) => n === 1 || (n === 2 && (Boolean(record) || busy === 'structure')) || (n === 3 && confirmed)
  const done = { 1: Boolean(record), 2: confirmed, 3: Boolean(summary) }
  const showTranscript = Boolean(transcript) || typing || busy === 'transcribe'
  const goView = (v) => { setView(v); setMenuOpen(false) }

  return (
    <div className="flex h-[100dvh] flex-col">
      <header className="shrink-0 border-b border-line bg-bg">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <button onClick={() => goView('consult')} className="flex shrink-0 items-center gap-2.5" aria-label="Vaidya Saathi, back to consultation">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent text-onaccent"><Icon name="mic" className="h-5 w-5" /></span>
            <span className="hidden text-lg font-semibold tracking-tight sm:inline">Vaidya Saathi</span>
          </button>
          {mock && <span className="rounded-full bg-orange-100 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-orange-800 dark:bg-orange-900/40 dark:text-orange-200">mock</span>}
          {view === 'consult' && <Stepper step={step} done={done} canReach={canReach} onGo={setStep} className="mx-auto hidden md:flex" />}
          <div className="ml-auto flex items-center gap-2">
            <label className="chip relative py-2 pl-3 pr-2" title="Language of the summary, alerts and share page">
              <Icon name="globe" className="h-4 w-4 text-muted" />
              <select aria-label="Language" className="max-w-[8.5rem] cursor-pointer appearance-none truncate bg-transparent pr-1 focus:outline-none sm:max-w-none"
                value={langChoice} onChange={(e) => setLangChoice(e.target.value)}>
                <option value="auto">{`Auto${langChoice === 'auto' && detected ? ` (${langName(detected)})` : ''}`}</option>
                {langs.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
            </label>
            <button className="icon-btn" onClick={toggleTheme} aria-label="Switch between dark and light theme" title="Switch theme">
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-4 w-4" />
            </button>
            <div className="relative">
              <button className="icon-btn" onClick={() => setMenuOpen((o) => !o)} aria-label="Menu" aria-expanded={menuOpen}><Icon name="menu" className="h-4 w-4" /></button>
              {menuOpen && (
                <>
                  <button className="fixed inset-0 z-10 cursor-default" aria-label="Close menu" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-2xl border border-line bg-surface p-1.5 shadow-2xl">
                    {VIEWS.map(([v, label, icon]) => (
                      <button key={v} onClick={() => goView(v)}
                        className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${view === v ? 'bg-accent-soft font-semibold' : 'hover:bg-accent-soft'}`}>
                        <Icon name={icon} className="h-4 w-4 text-muted" /> {label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        {view === 'consult' && <Stepper step={step} done={done} canReach={canReach} onGo={setStep} className="border-t border-line px-2 py-2 md:hidden" />}
      </header>

      {error && (
        <div className="shrink-0 px-4 pt-3">
          <div className="mx-auto flex max-w-3xl items-center gap-3 rounded-2xl border border-red-300 bg-red-50 px-4 py-2.5 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/60 dark:text-red-200" role="alert">
            <Icon name="alert" className="h-5 w-5" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError('')} aria-label="Dismiss" className="rounded-full p-1 hover:bg-red-100 dark:hover:bg-red-900/40"><Icon name="x" className="h-4 w-4" /></button>
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {view !== 'consult' ? (
          <div className="mx-auto max-w-6xl px-1 py-3">
            {view === 'history' ? <History /> : view === 'eval' ? <EvalPage /> : <Analytics />}
          </div>
        ) : step === 1 ? (
          /* 1. record: the big button is the first thing on screen */
          <div className={`mx-auto flex w-full max-w-3xl flex-col px-4 ${showTranscript ? 'gap-4 py-6' : 'min-h-full justify-center gap-10 py-10'}`}>
            {!showTranscript && (
              <div className="text-center">
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Record the visit</h1>
                <p className="mt-2 text-lg text-muted">Tap the button and talk with the patient as usual.</p>
              </div>
            )}
            <div className={showTranscript ? 'card p-4' : ''}>
              <Recorder compact={showTranscript} scenarioId={scenarioId} onAudio={onAudio} busy={busy === 'transcribe'} streaming={streaming}
                language={langChoice === 'auto' ? (detected || 'unknown') : langChoice} onLivePartial={livePartial} onLiveDone={liveDone} />
            </div>
            {showTranscript ? (
              <section className="card flex flex-col gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-accent-soft"><Icon name="chat" className="h-4 w-4" /></span>
                  <h2 className="font-semibold">What was said</h2>
                  <span className="ml-auto text-xs text-muted">Tap to fix any mistake</span>
                </div>
                <textarea className="input min-h-[11rem] resize-y text-[15px] leading-relaxed" placeholder={busy === 'transcribe' ? 'Writing down what was said…' : 'Type or paste the conversation here'}
                  value={transcript} onChange={(e) => { if (e.target.value.trim()) markStart(); setTranscript(e.target.value); setUtterances([]) }} />
                <DiarizedTranscript utterances={utterances} onSwap={swap} />
              </section>
            ) : (
              <div className="flex justify-center">
                <button className="btn-ghost" onClick={() => setTyping(true)}><Icon name="pen" className="h-4 w-4" /> Type it instead</button>
              </div>
            )}
            <OfflineQueue onUse={applyTranscript} />
            <DemoPicker scenarios={scenarios} value={scenarioId} onChange={pickScenario} disabled={Boolean(busy)} />
          </div>
        ) : step === 2 ? (
          /* 2. check: the extracted record, red flags first */
          <div className="mx-auto w-full max-w-5xl space-y-4 px-4 py-6">
            <Heading title="Check the details" sub={confirmed ? 'Signed and locked.' : 'Fix anything that is wrong, then sign at the bottom.'}>
              {record && (
                <div className="flex gap-1 rounded-full border border-line bg-surface p-1 sm:ml-auto">
                  {tabs.map(([k, label, icon]) => (
                    <button key={k} onClick={() => setTab(k)}
                      className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm transition ${tab === k ? 'bg-accent text-onaccent' : 'text-muted hover:text-ink'}`}>
                      <Icon name={icon} className="h-4 w-4" /> {label}
                    </button>
                  ))}
                </div>
              )}
            </Heading>
            {!record ? (
              <div className="card flex flex-col items-center gap-4 py-16 text-center">
                {busy === 'structure' ? (
                  <>
                    <Spinner className="h-12 w-12 border-4" />
                    <div className="text-xl font-semibold">Reading the conversation…</div>
                    <p className="text-muted">Finding complaints, vitals, medicines and advice.</p>
                  </>
                ) : (
                  <>
                    <Icon name="clipboard" className="h-12 w-12 text-muted" />
                    <div className="text-xl font-semibold">Nothing to check yet</div>
                    <button className="btn-outline" onClick={() => setStep(1)}><Icon name="left" className="h-4 w-4" /> Back to recording</button>
                  </>
                )}
              </div>
            ) : (
              <>
                {busy === 'structure' && <p className="flex items-center gap-2 text-sm text-muted"><Spinner className="h-4 w-4" /> Updating…</p>}
                <RedFlagBanner flags={record.red_flags} onPlay={playAlert} busy={busy === 'alert'} />
                {alertSrc && <audio controls autoPlay src={alertSrc} className="h-10 w-full" />}
                <SafetyWarnings warnings={record.safety_warnings} />
                {tab === 'record' && <RecordForm record={record} onChange={onRecordChange} locked={confirmed} />}
                {tab === 'evidence' && <SaidInferred record={record} />}
                {tab === 'photo' && vision && <PrescriptionPhoto record={record} />}
              </>
            )}
          </div>
        ) : (
          /* 3. patient: summary to play, then ways to hand it over */
          <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6">
            <Heading title={record?.patient.name ? `For ${record.patient.name}` : 'For the patient'} sub={`Summary in ${langName(lang)}${langChoice === 'auto' ? ' (auto)' : ''}. Only what the doctor prescribed.`} />
            {urgent && (
              <div className="flex flex-wrap items-center gap-3 rounded-3xl border-2 border-red-500 bg-red-50 p-4 dark:bg-red-950/40">
                <span className="grid h-11 w-11 place-items-center rounded-full bg-red-600 text-white"><Icon name="send" className="h-5 w-5" /></span>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold">Danger signs: refer to hospital</div>
                  {ticket ? <div className="text-sm"><b>{ticket.ticket_id}</b> <span className="text-muted">to {ticket.destination}, {new Date(ticket.created_at).toLocaleString()}</span></div>
                    : <div className="text-sm text-muted">Creates a referral ticket with this record.</div>}
                </div>
                {!ticket && <button disabled={busy === 'referral'} onClick={makeTicket} className="btn-danger">{busy === 'referral' ? <Spinner className="h-4 w-4" /> : <Icon name="send" className="h-4 w-4" />} Create referral ticket</button>}
              </div>
            )}
            <SummaryPlayer summary={summary} audioSrc={summary?.audio_base64 ? wavSrc(summary.audio_base64) : ''}
              canGenerate={confirmed} onGenerate={genSummary} busy={busy === 'summary'} langName={langName(lang)} />
            {confirmed && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">Give to the patient</h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <button disabled={busy === 'share'} onClick={makeShare} className="tile">
                    {busy === 'share' ? <Spinner className="h-7 w-7" /> : <Icon name="qr" className="h-7 w-7" />} Phone link (QR)
                  </button>
                  <button disabled={busy === 'card'} onClick={printCard} className="tile">
                    {busy === 'card' ? <Spinner className="h-7 w-7" /> : <Icon name="printer" className="h-7 w-7" />} Print card
                  </button>
                  <a className="tile" href={api.apiUrl(`/api/schedule.ics?record_id=${recordId}`)}><Icon name="calendar" className="h-7 w-7" /> Reminders</a>
                  <a className="tile" href={api.apiUrl(`/api/export/${recordId}.json`)} target="_blank" rel="noreferrer"><Icon name="download" className="h-7 w-7" /> Export (JSON)</a>
                </div>
                <label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" className="h-4 w-4" checked={includeDx} onChange={(e) => setIncludeDx(e.target.checked)} /> Show diagnosis on the phone page</label>
                {shareInfo && (
                  <div className="card flex flex-col items-center gap-4 sm:flex-row">
                    <img alt="QR code for the patient page" className="h-40 w-40 shrink-0 rounded-2xl bg-white p-2" src={`data:image/png;base64,${shareInfo.qr_png_base64}`} />
                    <div className="min-w-0 space-y-1 text-center sm:text-left">
                      <div className="text-lg font-semibold">Patient scans this with their phone</div>
                      <a className="link break-all text-sm" href={shareInfo.url} target="_blank" rel="noreferrer">{shareInfo.url}</a>
                      <div className="text-xs text-muted">Expires {new Date(shareInfo.expires_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                )}
              </section>
            )}
          </div>
        )}
      </div>

      <footer className="shrink-0 border-t border-line bg-bg">
        {view === 'consult' && (
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
            {step > 1 && (
              <button className="btn-outline h-12 shrink-0 px-4 sm:px-5" onClick={() => setStep(step - 1)} aria-label="Back">
                <Icon name="left" className="h-4 w-4" /> <span className="hidden sm:inline">Back</span>
              </button>
            )}
            {step === 1 && (
              <button disabled={!transcript.trim() || Boolean(busy)} onClick={extract} className="btn-accent btn-lg ml-auto w-full sm:w-auto">
                Extract details <Icon name="right" className="h-5 w-5" />
              </button>
            )}
            {step === 2 && record && <SignOff key={recordId ?? 'unsigned'} record={record} onSign={signOff} busy={busy === 'signoff'} />}
            {step === 2 && confirmed && (
              <button onClick={() => setStep(3)} className="btn-accent btn-lg ml-auto shrink-0">
                <span className="hidden sm:inline">Patient summary</span><span className="sm:hidden">Next</span> <Icon name="right" className="h-5 w-5" />
              </button>
            )}
            {step === 3 && (
              <button onClick={resetConsult} className="btn-accent btn-lg ml-auto">
                <Icon name="plus" className="h-5 w-5" /> New patient
              </button>
            )}
          </div>
        )}
        <p className="flex items-center justify-center gap-1.5 border-t border-amber-300/60 bg-amber-100 px-4 py-1.5 text-center text-xs font-medium text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/60 dark:text-amber-200">
          <Icon name="info" className="h-3.5 w-3.5" /> AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.
        </p>
      </footer>
    </div>
  )
}
