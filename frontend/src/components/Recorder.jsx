import { useEffect, useRef, useState } from 'react'

// M0 placeholder: no microphone yet. Record runs a timer, Stop sends a stub blob
// named after the chosen demo scenario; the mock API returns that scenario's transcript.
export default function Recorder({ scenarioId, onTranscribe, busy }) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const timer = useRef(null)

  useEffect(() => () => clearInterval(timer.current), [])

  const start = () => {
    setSeconds(0)
    setRecording(true)
    timer.current = setInterval(() => setSeconds((s) => s + 1), 1000)
  }
  const stop = () => {
    clearInterval(timer.current)
    setRecording(false)
    onTranscribe(new Blob(['placeholder'], { type: 'audio/webm' }), `${scenarioId || 'S1'}.webm`)
  }

  return (
    <div className="space-y-2">
      <button
        disabled={busy}
        onClick={recording ? stop : start}
        className={`w-full py-4 rounded text-white text-lg font-semibold disabled:opacity-50 ${recording ? 'bg-red-600 animate-pulse' : 'bg-blue-700'}`}
      >
        {recording ? `Stop (${seconds}s)` : 'Record (placeholder)'}
      </button>
      <p className="text-xs text-gray-600">Real microphone capture arrives in M1. Pick a demo scenario first.</p>
    </div>
  )
}
