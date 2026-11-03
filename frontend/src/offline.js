// Offline-first capture: recordings made without a network wait in IndexedDB (audio only until synced, then the
// transcript is kept and the audio is dropped). Every item has a client-generated id so the server can ignore repeats.
const DB = 'vs-offline'
const STORE = 'queue'

const open = () => new Promise((resolve, reject) => {
  const req = indexedDB.open(DB, 1)
  req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' })
  req.onsuccess = () => resolve(req.result)
  req.onerror = () => reject(req.error)
})

async function tx(mode, fn) {
  const db = await open()
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode)
    const out = fn(t.objectStore(STORE))
    t.oncomplete = () => { db.close(); resolve(out.result) }
    t.onerror = () => reject(t.error)
  })
}

const changed = () => window.dispatchEvent(new Event('offline-queue'))

export async function enqueue(blob, filename) {
  const item = { id: crypto.randomUUID(), blob, filename, status: 'queued', created: Date.now(), error: '', result: null }
  await tx('readwrite', (s) => s.put(item))
  changed()
  return item.id
}
export const list = () => tx('readonly', (s) => s.getAll()).then((xs) => xs.sort((a, b) => a.created - b.created))
const update = async (id, patch) => {
  const [item] = (await list()).filter((x) => x.id === id)
  if (item) await tx('readwrite', (s) => s.put({ ...item, ...patch }))
  changed()
}
export const remove = async (id) => { await tx('readwrite', (s) => s.delete(id)); changed() }

let syncing = false
// Sends every queued or failed item to /api/sync one by one. Safe to call repeatedly (and on every reconnect).
export async function syncAll() {
  if (syncing || !navigator.onLine) return
  syncing = true
  try {
    for (const item of (await list()).filter((x) => x.status === 'queued' || x.status === 'failed')) {
      await update(item.id, { status: 'syncing', error: '' })
      try {
        const form = new FormData()
        form.append('client_id', item.id)
        form.append('audio', item.blob, item.filename)
        const res = await fetch('/api/sync', { method: 'POST', body: form })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || `Sync failed (${res.status})`)
        await update(item.id, { status: 'done', result: data, blob: null })
      } catch (e) {
        await update(item.id, { status: 'failed', error: e.message })
      }
    }
  } finally {
    syncing = false
  }
}
