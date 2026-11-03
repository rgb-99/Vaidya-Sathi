import { useEffect, useRef, useState } from 'react'
import { startLive } from '../stream.js'

const MAX_SECONDS = 180 // matches MAX_AUDIO_SECONDS on the backend
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

function micError(e) {
  if (!navigator.mediaDevices?.getUserMedia) return 'Microphone is not available in this browser (it needs https or localhost). Upload a file instead.'
  if (e.name === 'NotAllowedError' || e.name === 'SecurityError') return 'Microphone permission was denied. Allow it in the browser address bar, or upload a file instead.'
  if (e.name === 'NotFoundError') return 'No microphone found. Upload a file instead.'
  return `Could not start recording: ${e.message}`
}

export default function Recorder({ scenarioId, onAudio, busy, streaming, language, onLivePartial, onLiveDone }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const stopLive = useRef(null)
  const recorder = useRef(null)
  const timer = useRef(null)
  const fileInput = useRef(null)
  // In mock mode the backend picks the canned transcript from the filename, so keep the scenario id in it.
  const baseName = scenarioId || 'recording'

  useEffect(() => () => {
    clearInterval(timer.current)
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }, [])

  const stop = () => {
    clearInterval(timer.current)
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

  return (
    <div className="space-y-2">
      <button
        disabled={busy}
        onClick={recording ? stop : start}
        className={`w-full rounded-full py-4 text-lg font-medium transition disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${recording ? 'bg-red-600 text-white animate-pulse' : 'bg-accent text-onaccent hover:bg-accent-dark'}`}
      >
        {busy ? 'Transcribing…' : recording ? `Stop  ${fmt(seconds)}` : 'Record'}
      </button>
      {streaming && (
        <button disabled={busy || recording} onClick={live ? () => { stopLive.current(); } : goLive}
          className={`btn w-full border border-line ${live ? 'bg-red-600 text-white animate-pulse' : 'bg-surface'}`}>
          {live ? 'Stop live transcription' : 'Record live (words appear as you speak)'}
        </button>
      )}
      <div className="flex items-center gap-3 text-sm">
        <input ref={fileInput} type="file" accept="audio/*" onChange={onFile} className="hidden" />
        <button disabled={busy || recording} onClick={() => fileInput.current.click()} className="link">
          or upload an audio file
        </button>
        <span className="ml-auto font-mono text-xs text-muted">max {fmt(MAX_SECONDS)}</span>
      </div>
      {error && <p className="text-sm text-red-700 dark:text-red-300 dark:text-red-300" role="alert">{error}</p>}
    </div>
  )
}
