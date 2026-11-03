import { useState } from 'react'

export default function SignOff({ record, onSign, busy }) {
  const [name, setName] = useState('')
  if (record.signed_off_by) {
    return (
      <div className="rounded-xl border border-green-300 bg-green-50 px-3 py-2 text-sm dark:border-green-800 dark:bg-green-950/40" role="status">
        <b>Signed off and locked</b> by {record.signed_off_by}, {new Date(record.signed_at).toLocaleString()}
      </div>
    )
  }
  return (
    <div className="flex items-end gap-2 rounded-xl border border-line bg-bg p-2">
      <label className="min-w-0 flex-1"><span className="label">Clinician name (needed to sign off; summary, referral and export stay locked until then)</span>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Dr …" />
      </label>
      <button disabled={!name.trim() || busy} onClick={() => onSign(name.trim())} className="btn-ink shrink-0">
        {busy ? 'Signing…' : 'Sign off and lock'}
      </button>
    </div>
  )
}
