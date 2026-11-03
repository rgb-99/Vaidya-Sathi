export default function SummaryPlayer({ summary, audioSrc, canGenerate, onGenerate, busy, children }) {
  return (
    <div className="space-y-4">
      <button disabled={!canGenerate || busy} onClick={onGenerate} className="btn-accent w-full">
        {busy ? 'Generating…' : 'Generate patient summary'}
      </button>
      {!canGenerate && <p className="text-xs text-muted">Confirm the record first.</p>}
      {summary?.used_fallback && <p className="text-xs text-muted">Built from a fixed template because the AI summary failed the safety check.</p>}
      {summary && <p className="rounded-xl border border-line bg-bg p-4 text-base leading-relaxed">{summary.text}</p>}
      {summary && !audioSrc && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm" role="alert">
          Audio failed: {summary.audio_error || 'unknown error'} <button className="link ml-2" onClick={onGenerate}>Retry</button>
        </div>
      )}
      {audioSrc ? (
        <>
          <audio controls src={audioSrc} className="w-full" />
          <a className="link text-sm" href={audioSrc} download="summary.wav">Download audio</a>
        </>
      ) : !summary && (
        <div className="rounded-xl border border-dashed border-line p-4 text-center text-sm text-muted">Audio player placeholder</div>
      )}
      {children}
    </div>
  )
}
