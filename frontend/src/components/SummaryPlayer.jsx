export default function SummaryPlayer({ summary, audioSrc, canGenerate, onGenerate, busy, children }) {
  return (
    <div className="space-y-4">
      <button disabled={!canGenerate || busy} onClick={onGenerate} className="btn-accent w-full">
        {busy ? 'Generating…' : 'Generate patient summary'}
      </button>
      {!canGenerate && <p className="text-xs text-muted">Confirm the record first.</p>}
      {summary && <p className="rounded-xl border border-line bg-bg p-4 text-base leading-relaxed">{summary.text}</p>}
      {audioSrc ? (
        <>
          <audio controls src={audioSrc} className="w-full" />
          <a className="link text-sm" href={audioSrc} download="summary.wav">Download audio</a>
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-line p-4 text-center text-sm text-muted">Audio player placeholder</div>
      )}
      {children}
    </div>
  )
}
