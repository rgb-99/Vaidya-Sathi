import { useEffect, useRef, useState } from 'react'
import { startLive } from '../stream.js'
import Icon, { Spinner } from './Icon.jsx'

const MAX_SECONDS = 180 // matches MAX_AUDIO_SECONDS on the backend
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

function micError(e) {
  if (!navigator.mediaDevices?.getUserMedia) return 'Microphone is not available in this browser (it needs https or localhost). Upload a file instead.'
  if (e.name === 'NotAllowedError' || e.name === 'SecurityError') return 'Microphone permission was denied. Allow it in the browser address bar, or upload a file instead.'
  if (e.name === 'NotFoundError') return 'No microphone found. Upload a file instead.'
  return `Could not start recording: ${e.message}`
}

// One big button: tap to start, tap to stop. `compact` is used once a transcript exists, to leave room for it.
export default function Recorder({ scenarioId, onAudio, busy, streaming, language, onLivePartial, onLiveDone, compact }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const stopLive = useRef(null)
  const recorder = useRef(null)
  const timer = useRef(null)
  const fileInput = useRef(null)
  const ring = useRef(null)     // grows with the microphone level, so the user can see they are being heard
  const meter = useRef(null)
  // In mock mode the backend picks the canned transcript from the filename, so keep the scenario id in it.
  const baseName = scenarioId || 'recording'

  const stopMeter = () => {
    if (!meter.current) return
    cancelAnimationFrame(meter.current.raf)
    meter.current.ctx.close().catch(() => {})
    meter.current = null
  }
  const startMeter = (stream) => {
    try {
      const ctx = new AudioContext()
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      ctx.createMediaStreamSource(stream).connect(analyser)
      const data = new Uint8Array(analyser.fftSize)
      const tick = () => {
        analyser.getByteTimeDomainData(data)
        let peak = 0
        for (const v of data) peak = Math.max(peak, Math.abs(v - 128))
        if (ring.current) ring.current.style.transform = `scale(${1 + Math.min(peak / 64, 1) * 0.35})`
        meter.current.raf = requestAnimationFrame(tick)
      }
      meter.current = { ctx, raf: 0 }
      tick()
    } catch { /* the level ring is decoration only */ }
  }

  useEffect(() => () => {
    clearInterval(timer.current)
    stopMeter()
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }, [])

  const stop = () => {
    clearInterval(timer.current)
    stopMeter()
    if (recorder.current?.state === 'recording') recorder.current.stop()
    setRecording(false)
  }

  const start = async () => {
    setError('')
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      setError(micError(e))
      return
    }
    const mimeType = MIME_TYPES.find((t) => window.MediaRecorder?.isTypeSupported(t)) || ''
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    const chunks = []
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data)
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      const type = rec.mimeType || 'audio/webm'
      const ext = type.includes('mp4') ? 'mp4' : type.includes('ogg') ? 'ogg' : 'webm'
      if (chunks.length) onAudio(new Blob(chunks, { type }), `${baseName}.${ext}`)
      else setError('Nothing was recorded. Try again.')
    }
    recorder.current = rec
    rec.start()
    startMeter(stream)
    setSeconds(0)
    setRecording(true)
    timer.current = setInterval(() => {
      setSeconds((s) => {
        if (s + 1 >= MAX_SECONDS) stop()
        return s + 1
      })
    }, 1000)
  }

  const goLive = async () => {
    setError('')
    try {
      stopLive.current = await startLive({
        language, scenario: scenarioId,
        onPartial: onLivePartial,
        onDone: (t) => { setLive(false); onLiveDone(t) },
        onError: (m) => { setLive(false); setError(m) },
      })
      setLive(true)
    } catch (e) {
      setError(micError(e))
    }
  }

  const onFile = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError('')
    onAudio(file, file.name)
  }

  const active = recording || live
  const size = compact ? 'h-20 w-20' : 'h-40 w-40 sm:h-48 sm:w-48'
  const status = busy ? 'Writing down what was said…'
    : live ? 'Listening live. Words appear below.'
    : recording ? 'Listening… tap to stop'
    : compact ? 'Tap to record again' : 'Tap to start recording'

  return (
    <div className={compact ? 'flex items-center gap-4' : 'flex flex-col items-center gap-5'}>
      <div className="relative grid shrink-0 place-items-center">
        {recording && <span ref={ring} className={`absolute rounded-full bg-red-500/25 transition-transform duration-75 ${size}`} />}
        {active && <span className={`absolute animate-ping rounded-full bg-red-500/20 ${size}`} />}
        <button
          disabled={busy || live}
          onClick={recording ? stop : start}
          aria-label={recording ? 'Stop recording' : 'Start recording'}
          className={`relative grid place-items-center rounded-full shadow-xl transition active:scale-95 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-accent ${size}
            ${active ? 'bg-red-600 text-white shadow-red-600/30' : 'bg-accent text-onaccent hover:scale-[1.03]'} ${busy ? 'opacity-60' : ''}`}
        >
          {busy ? <Spinner className={compact ? 'h-8 w-8' : 'h-14 w-14 border-4'} />
            : <Icon name={recording ? 'stop' : 'mic'} className={compact ? 'h-9 w-9' : 'h-16 w-16 sm:h-20 sm:w-20'} />}
        </button>
      </div>

      <div className={compact ? 'min-w-0 flex-1 space-y-2' : 'flex flex-col items-center gap-4 text-center'}>
        <div>
          {recording && <div className={`font-mono font-semibold tabular-nums ${compact ? 'text-xl' : 'text-4xl'}`}>{fmt(seconds)}</div>}
          <p className={`${compact ? 'text-sm' : 'text-lg'} ${recording ? 'text-red-600 dark:text-red-400' : 'text-muted'}`} aria-live="polite">{status}</p>
          {!compact && !recording && !busy && <p className="mt-1 text-xs text-muted">Up to {fmt(MAX_SECONDS)} minutes</p>}
        </div>
        <div className={`flex flex-wrap gap-2 ${compact ? '' : 'justify-center'}`}>
          <input ref={fileInput} type="file" accept="audio/*" onChange={onFile} className="hidden" />
          <button disabled={busy || active} onClick={() => fileInput.current.click()} className="chip">
            <Icon name="upload" className="h-4 w-4" /> Upload audio
          </button>
          {streaming && (
            <button disabled={busy || recording} onClick={live ? () => stopLive.current() : goLive}
              className={`chip ${live ? 'border-red-600 bg-red-600 text-white' : ''}`}>
              <Icon name={live ? 'stop' : 'live'} className="h-4 w-4" /> {live ? 'Stop live' : 'Live (words as you speak)'}
            </button>
          )}
        </div>
        {error && <p className="max-w-md text-sm text-red-700 dark:text-red-300" role="alert">{error}</p>}
      </div>
    </div>
  )
}
