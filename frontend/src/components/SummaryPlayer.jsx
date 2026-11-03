export default function SummaryPlayer({ summary, audioSrc, canGenerate, onGenerate, busy, children }) {
  return (
    <>
      <button disabled={!canGenerate || busy} onClick={onGenerate} className="btn-accent w-full shrink-0">
        {busy ? 'Generating…' : 'Generate patient summary'}
      </button>
      {!canGenerate && <p className="shrink-0 text-xs text-muted">Sign off the record first.</p>}
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
        {summary?.used_fallback && <p className="text-xs text-muted">Built from a fixed template because the AI summary failed the safety check.</p>}
        {summary && <p className="rounded-xl border border-line bg-bg p-3 text-sm leading-relaxed">{summary.text}</p>}
        {summary && !audioSrc && (
          <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/40 p-2 text-sm dark:border-red-900 dark:bg-red-950/40" role="alert">
            Audio failed: {summary.audio_error || 'unknown error'} <button className="link ml-2" onClick={onGenerate}>Retry</button>
          </div>
        )}
        {audioSrc && (
          <>
            <audio controls src={audioSrc} className="h-9 w-full" />
            <a className="link text-xs" href={audioSrc} download="summary.wav">Download audio</a>
          </>
        )}
        {!summary && <div className="rounded-xl border border-dashed border-line p-3 text-center text-xs text-muted">The summary and its audio appear here</div>}
      </div>
      {children}
    </>
  )
}
