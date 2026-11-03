import { useEffect, useState } from 'react'
import { list, remove, syncAll } from '../offline.js'

const CHIP = { queued: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200', syncing: 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-200', done: 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200', failed: 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200' }

export default function OfflineQueue({ onUse }) {
  const [items, setItems] = useState([])
  const [online, setOnline] = useState(navigator.onLine)
  useEffect(() => {
    const refresh = () => list().then(setItems).catch(() => {})
    const up = () => { setOnline(true); syncAll() }   // automatic sync on reconnect
    const down = () => setOnline(false)
    refresh()
    window.addEventListener('offline-queue', refresh)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    if (navigator.onLine) syncAll()
    return () => { window.removeEventListener('offline-queue', refresh); window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [])
  if (!items.length && online) return null
  return (
    <div className="space-y-2 rounded-xl border border-line bg-bg p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="label mb-0">{online ? 'Saved recordings' : 'Offline: recordings are saved on this device'}</span>
        <button className="link text-xs" disabled={!online} onClick={syncAll}>Sync now</button>
      </div>
      {items.map((it) => (
        <div key={it.id} className="flex items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 font-mono text-[11px] uppercase ${CHIP[it.status]}`}>{it.status}</span>
          <span className="truncate">{it.filename}</span>
          {it.status === 'failed' && <span className="text-xs text-red-700 dark:text-red-300 dark:text-red-300">{it.error}</span>}
          {it.status === 'done' && <button className="link ml-auto text-xs" onClick={() => { onUse(it.result); remove(it.id) }}>Use transcript</button>}
          {it.status !== 'syncing' && <button className="link text-xs" onClick={() => remove(it.id)}>Delete</button>}
        </div>
      ))}
    </div>
  )
}
