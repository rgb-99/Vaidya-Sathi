// Calls the backend using the contract in SPEC TRD section 6.
// VITE_API_BASE is the backend origin when it is hosted apart from the frontend (empty: same origin, the Vite proxy in dev).
export const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')
export const apiUrl = (path) => API_BASE + path

// Requests that are safe to repeat are retried when the connection drops or the server is still starting (a hosted
// backend that scaled to zero takes a few seconds to wake). Calls that store something (sign-off, referral, share,
// baseline) are never retried, so they cannot be created twice.
const RETRY_DELAYS_MS = [1000, 2000, 3000, 4000]
const REPEATABLE_POSTS = ['/transcribe', '/structure', '/redflags', '/safety', '/summary', '/alert-audio', '/reconcile']
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function request(path, options) {
  const repeatable = !options?.method || options.method === 'GET' || REPEATABLE_POSTS.includes(path)
  const retries = repeatable ? RETRY_DELAYS_MS : []
  let res
  for (let i = 0; ; i++) {
    try {
      res = await fetch(apiUrl('/api' + path), options)
      if (![502, 503, 504].includes(res.status) || i >= retries.length) break
    } catch {
      if (i >= retries.length) throw new Error('Could not connect to the server. Check your internet connection and try again.')
    }
    await wait(retries[i])
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
  return data
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const health = () => request('/health')
export const getScenarios = () => request('/demo/scenarios')

export const transcribe = (blob, filename) => {
  const form = new FormData()
  form.append('audio', blob, filename)
  return request('/transcribe', { method: 'POST', body: form })
}

export const structure = (transcript, utterances = []) => post('/structure', { transcript, utterances })
export const getLanguages = () => request('/languages')
export const redflags = (record) => post('/redflags', record)
export const summary = (record, language) => post('/summary', { record, language })
export const alertAudio = (red_flags, language) => post('/alert-audio', { red_flags, language })
export const referral = (record, record_id) => post('/referral', { record, confirmed: true, record_id })

export const signoff = (record, clinician_name, started_at = '', demo = false) => post('/signoff', { record, clinician_name, started_at, demo })
export const getRecords = () => request('/records')
export const getTickets = () => request('/tickets')
export const getCardHtml = async (record) => {
  const res = await fetch(apiUrl('/api/card'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record) })
  if (!res.ok) throw new Error('Could not build the printable card.')
  return res.text()
}

export const safety = (record) => post('/safety', record)
export const share = (record, language, include_diagnosis) => post('/share', { record, language, include_diagnosis })
export const reconcile = (record, previous) => post('/reconcile', { record, previous })
export const features = () => request('/features')
