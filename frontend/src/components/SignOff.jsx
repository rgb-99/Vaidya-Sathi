import { useState } from 'react'

export default function SignOff({ record, onSign, busy }) {
  const [name, setName] = useState('')
  if (record.signed_off_by) {
    return (
      <div className="rounded-xl border border-green-300 bg-green-50 p-3 text-sm" role="status">
        <div className="font-semibold">Signed off and locked</div>
        <div>{record.signed_off_by}, {new Date(record.signed_at).toLocaleString()}</div>
      </div>
    )
  }
  return (
    <div className="space-y-2 rounded-xl border border-line bg-bg p-3">
      <label className="block"><span className="label">Clinician name (required to sign off)</span>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Dr …" />
      </label>
      <button disabled={!name.trim() || busy} onClick={() => onSign(name.trim())} className="btn-ink w-full">
        {busy ? 'Signing…' : 'Sign off and lock record'}
      </button>
      <p className="text-xs text-muted">Summary audio, referral and export stay disabled until the record is signed.</p>
    </div>
  )
}
