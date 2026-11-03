// Calls the backend using the contract in SPEC TRD section 6.
async function request(path, options) {
  const res = await fetch('/api' + path, options)
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

export const structure = (transcript) => post('/structure', { transcript })
export const redflags = (record) => post('/redflags', record)
export const summary = (record, language) => post('/summary', { record, language })
export const alertAudio = (red_flags, language) => post('/alert-audio', { red_flags, language })
export const referral = (record) => post('/referral', { record, confirmed: true })
