// Calls the backend using the contract in SPEC TRD section 6.
async function request(path, options) {
  let res
  try {
    res = await fetch('/api' + path, options)
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running and your network is up.')
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

export const signoff = (record, clinician_name) => post('/signoff', { record, clinician_name })
export const getRecords = () => request('/records')
export const getTickets = () => request('/tickets')
export const getCardHtml = async (record) => {
  const res = await fetch('/api/card', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record) })
  if (!res.ok) throw new Error('Could not build the printable card.')
  return res.text()
}

export const safety = (record) => post('/safety', record)
export const share = (record, language, include_diagnosis) => post('/share', { record, language, include_diagnosis })
export const reconcile = (record, previous) => post('/reconcile', { record, previous })
export const features = () => request('/features')
