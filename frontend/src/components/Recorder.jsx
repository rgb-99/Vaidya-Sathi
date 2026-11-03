import { useEffect, useRef, useState } from 'react'

const MAX_SECONDS = 180 // matches MAX_AUDIO_SECONDS on the backend
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

function micError(e) {
  if (!navigator.mediaDevices?.getUserMedia) return 'Microphone is not available in this browser (it needs https or localhost). Upload a file instead.'
  if (e.name === 'NotAllowedError' || e.name === 'SecurityError') return 'Microphone permission was denied. Allow it in the browser address bar, or upload a file instead.'
  if (e.name === 'NotFoundError') return 'No microphone found. Upload a file instead.'
  return `Could not start recording: ${e.message}`
}

export default function Recorder({ scenarioId, onAudio, busy }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState('')
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
        className={`w-full py-4 rounded text-white text-lg font-semibold disabled:opacity-50 ${recording ? 'bg-red-600 animate-pulse' : 'bg-blue-700'}`}
      >
        {busy ? 'Transcribing…' : recording ? `Stop  ${fmt(seconds)}` : 'Record'}
      </button>
      <div className="flex items-center gap-2 text-sm">
        <input ref={fileInput} type="file" accept="audio/*" onChange={onFile} className="hidden" />
        <button disabled={busy || recording} onClick={() => fileInput.current.click()} className="text-blue-700 underline disabled:opacity-40">
          or upload an audio file
        </button>
        <span className="text-gray-500">max {fmt(MAX_SECONDS)}</span>
      </div>
      {error && <p className="text-sm text-red-700" role="alert">{error}</p>}
    </div>
  )
}
