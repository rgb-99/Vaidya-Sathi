import { useState } from 'react'
import Icon, { Spinner } from './Icon.jsx'

// Lives in the bottom bar of the Check step: the doctor types their name and signs, which locks the record.
export default function SignOff({ record, onSign, busy }) {
  const [name, setName] = useState('')
  if (record.signed_off_by) {
    return (
      <div className="flex min-w-0 items-center gap-2 text-sm text-green-700 dark:text-green-400" role="status">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-green-600 text-white"><Icon name="check" className="h-4 w-4" /></span>
        <span className="truncate">Signed by <b>{record.signed_off_by}</b> · locked</span>
      </div>
    )
  }
  return (
    <form className="flex min-w-0 flex-1 items-center gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) onSign(name.trim()) }}>
      <label className="relative min-w-0 flex-1">
        <span className="sr-only">Doctor name (needed to sign off; summary, referral and export stay locked until then)</span>
        <Icon name="pen" className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input className="input h-12 rounded-full pl-10" value={name} onChange={(e) => setName(e.target.value)} placeholder="Doctor name, to sign" />
      </label>
      <button type="submit" disabled={!name.trim() || busy} className="btn-accent h-12 shrink-0 px-6">
        {busy ? <Spinner className="h-4 w-4" /> : <Icon name="lock" className="h-4 w-4" />} <span className="hidden sm:inline">Sign and lock</span><span className="sm:hidden">Sign</span>
      </button>
    </form>
  )
}
