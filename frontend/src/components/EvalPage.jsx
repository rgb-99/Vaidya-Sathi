import { useEffect, useState } from 'react'
import { apiUrl } from '../api.js'

const HEADLINE = [
  ['overall_f1', 'Overall field F1 (%)'], ['drug_exact', 'Drug name exact match (%)'], ['dose_exact', 'Dose exact match (%)'],
  ['redflag_precision', 'Red-flag precision (%)'], ['redflag_recall', 'Red-flag recall (%)'], ['hallucinations', 'Hallucinations (must be 0)'],
  ['speaker_accuracy', 'Speaker-label accuracy (%)'], ['extraction_failures', 'Extraction failures'],
]
const fmt = (v) => (v === null || v === undefined ? 'n/a' : v)

export default function EvalPage() {
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    fetch(apiUrl('/api/eval/latest')).then(async (r) => (r.ok ? setReport(await r.json()) : setError((await r.json()).error))).catch(() => setError('Cannot reach the server.'))
  }, [])
  if (error) return <main className="w-full p-3"><p className="text-red-700 dark:text-red-300 dark:text-red-300" role="alert">{error}</p></main>
  if (!report) return <main className="w-full p-3 text-muted">Loading…</main>
  const m = report.metrics
  const prev = report.previous && report.previous.mode === report.mode ? report.previous.metrics : null
  const delta = (k) => (prev && typeof m[k] === 'number' && typeof prev[k] === 'number' ? (m[k] - prev[k]).toFixed(1) : '')
  return (
    <main className="grid w-full gap-3 p-3 lg:grid-cols-[1fr_1.6fr]">
      <div className="space-y-3"><section className="card space-y-2">
        <div className="eyebrow">Latest evaluation</div>
        <p className="text-sm">Run {report.run_id}, mode <b>{report.mode}</b>, <b>{report.scenario_count}</b> scenarios. {report.synthetic}</p>
        <p className="text-xs text-muted">LLM {report.config.llm_model}, STT {report.config.stt_model}/{report.config.stt_mode}, prompt {report.config.prompt_version}. Gate: {report.gate.passed ? 'passed' : 'FAILED: ' + report.gate.failures.join('; ')}</p>
      </section>
      <section className="card space-y-2">
        <div className="eyebrow">Scenarios with the most issues</div>
        {report.scenarios.filter((s) => s.issues).slice(0, 6).map((s) => (
          <div key={s.id} className="rounded-xl border border-line bg-bg p-2 text-sm">
            <b>{s.id}</b> <span className="text-muted">{s.issues} issues{s.extraction_failed ? ', extraction failed' : ''}</span>
            <div className="text-xs text-muted">missed: {s.missed.map((f) => f[2]).join('; ') || 'none'}</div>
          </div>
        ))}
      </section></div>
      <section className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-muted"><th className="py-1">Metric</th><th>Now</th><th>Previous run</th><th>Change</th></tr></thead>
          <tbody>
            {HEADLINE.map(([k, label]) => (
              <tr key={k} className="border-t border-line"><td className="py-1">{label}</td><td className="font-mono">{fmt(m[k])}</td>
                <td className="font-mono text-muted">{prev ? fmt(prev[k]) : 'n/a'}</td><td className="font-mono">{delta(k)}</td></tr>
            ))}
            {Object.entries(m.per_field).map(([g, v]) => (
              <tr key={g} className="border-t border-line"><td className="py-1">F1: {g} <span className="text-muted">({v.expected} expected)</span></td><td className="font-mono">{fmt(v.f1)}</td><td className="font-mono text-muted">{prev?.per_field?.[g] ? fmt(prev.per_field[g].f1) : 'n/a'}</td><td /></tr>
            ))}
            {Object.entries(m.latency_s).map(([s, v]) => (
              <tr key={s} className="border-t border-line"><td className="py-1">Latency {s} (s)</td><td className="font-mono">p50 {v.p50}, p95 {v.p95}</td><td className="font-mono text-muted">{prev?.latency_s?.[s] ? `p50 ${prev.latency_s[s].p50}, p95 ${prev.latency_s[s].p95}` : 'n/a'}</td><td /></tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}
