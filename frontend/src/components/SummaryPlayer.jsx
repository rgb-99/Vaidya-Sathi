import { useEffect, useRef, useState } from 'react'
import Icon, { Spinner } from './Icon.jsx'

// A single large play button with a progress bar: easier to use than the browser's small audio controls.
export function BigPlay({ src, label = 'Play' }) {
  const audio = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  useEffect(() => { setPlaying(false); setProgress(0) }, [src])
  const toggle = () => (audio.current.paused ? audio.current.play() : audio.current.pause())
  return (
    <div className="flex items-center gap-4">
      <audio ref={audio} src={src} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { setPlaying(false); setProgress(0) }}
        onTimeUpdate={(e) => setProgress(e.target.duration ? e.target.currentTime / e.target.duration : 0)} />
      <button onClick={toggle} aria-label={playing ? 'Pause' : label}
        className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-accent text-onaccent shadow-lg transition hover:scale-105 active:scale-95">
        <Icon name={playing ? 'pause' : 'play'} className="h-7 w-7" />
      </button>
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 text-sm font-medium">{playing ? 'Playing…' : label}</div>
        <div className="h-2 overflow-hidden rounded-full bg-accent-soft">
          <div className="h-full rounded-full bg-accent transition-[width] duration-200" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>
    </div>
  )
}

export default function SummaryPlayer({ summary, audioSrc, canGenerate, onGenerate, busy, langName }) {
  if (!summary) {
    return (
      <div className="card flex flex-col items-center gap-4 py-10 text-center">
        <span className="grid h-20 w-20 place-items-center rounded-full bg-accent-soft"><Icon name="volume" className="h-9 w-9" /></span>
        <div>
          <h2 className="text-2xl font-semibold">Make the patient summary</h2>
          <p className="mt-1 text-muted">Simple words the patient can hear, in {langName}.</p>
        </div>
        <button disabled={!canGenerate || busy} onClick={onGenerate} className="btn-accent btn-lg">
          {busy ? <><Spinner className="h-5 w-5" /> Making summary…</> : <><Icon name="volume" className="h-5 w-5" /> Make summary</>}
        </button>
        {!canGenerate && <p className="text-xs text-muted">Sign off the record first.</p>}
      </div>
    )
  }
  return (
    <div className="card space-y-5">
      {audioSrc ? <BigPlay src={audioSrc} label={`Play for patient (${langName})`} /> : (
        <div className="flex items-center gap-3 rounded-2xl bg-red-50 p-3 text-sm dark:bg-red-950/40" role="alert">
          <Icon name="alert" className="h-5 w-5 text-red-600" />
          <span className="flex-1">Audio failed: {summary.audio_error || 'unknown error'}</span>
          <button className="btn-outline px-4 py-1.5" onClick={onGenerate} disabled={busy}>{busy ? <Spinner className="h-4 w-4" /> : 'Retry'}</button>
        </div>
      )}
      <p className="text-lg leading-relaxed">{summary.text}</p>
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
        {summary.used_fallback && <span>Built from a fixed template because the AI summary failed the safety check.</span>}
        {audioSrc && <a className="ml-auto inline-flex items-center gap-1 hover:text-ink" href={audioSrc} download="summary.wav"><Icon name="download" className="h-3.5 w-3.5" /> Download audio</a>}
        {audioSrc && <button className="inline-flex items-center gap-1 hover:text-ink disabled:opacity-40" onClick={onGenerate} disabled={busy}><Icon name="volume" className="h-3.5 w-3.5" /> Make again</button>}
      </div>
    </div>
  )
}
