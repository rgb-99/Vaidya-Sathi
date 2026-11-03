// Live transcription: microphone -> 16 kHz mono WAV chunks (about 1 s each) -> /api/stream -> text segments.
// ScriptProcessorNode is deprecated but works in every browser without a separate worklet file.
import { API_BASE } from './api.js'

function wavChunk(samples) {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buf)
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
  str(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); str(8, 'WAVEfmt ')
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true)
  v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
  str(36, 'data'); v.setUint32(40, samples.length * 2, true)
  samples.forEach((s, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 0x7fff, true))
  return buf
}

// ws(s):// origin of the backend: API_BASE when set, else this page's host.
const wsBase = () => (API_BASE ? API_BASE.replace(/^http/, 'ws') : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`)

export async function startLive({ language, scenario, onPartial, onDone, onError }) {
  const media = await navigator.mediaDevices.getUserMedia({ audio: true })
  const ctx = new AudioContext({ sampleRate: 16000 })
  const source = ctx.createMediaStreamSource(media)
  const node = ctx.createScriptProcessor(4096, 1, 1)
  const ws = new WebSocket(`${wsBase()}/api/stream?language=${encodeURIComponent(language || 'unknown')}&scenario=${scenario || 'S1'}`)
  let pending = []
  let count = 0
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.type === 'partial') onPartial(m.text)
    else if (m.type === 'done') { onDone(m.transcript); ws.close() }
    else if (m.type === 'error') { onError(m.error); ws.close() }
  }
  ws.onerror = () => onError('Live connection failed. Use the normal recorder.')
  node.onaudioprocess = (e) => {
    pending.push(...e.inputBuffer.getChannelData(0))
    count += 4096
    if (count >= 16000 && ws.readyState === WebSocket.OPEN) {
      ws.send(wavChunk(Float32Array.from(pending)))
      pending = []; count = 0
    }
  }
  source.connect(node); node.connect(ctx.destination)
  return () => {   // stop
    node.disconnect(); source.disconnect(); media.getTracks().forEach((t) => t.stop()); ctx.close()
    if (ws.readyState === WebSocket.OPEN) {
      if (pending.length) ws.send(wavChunk(Float32Array.from(pending)))
      ws.send('end')
    }
  }
}
