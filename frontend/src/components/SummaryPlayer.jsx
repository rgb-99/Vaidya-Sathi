export default function SummaryPlayer({ summary, audioSrc, canGenerate, onGenerate, busy, children }) {
  return (
    <div className="space-y-3">
      <button disabled={!canGenerate || busy} onClick={onGenerate} className="w-full bg-green-700 text-white rounded py-2 disabled:opacity-40">
        {busy ? 'Generating…' : 'Generate patient summary'}
      </button>
      {!canGenerate && <p className="text-xs text-gray-600">Confirm the record first.</p>}
      {summary && <p className="border rounded p-2 bg-white">{summary.text}</p>}
      {audioSrc && (
        <>
          <audio controls src={audioSrc} className="w-full" />
          <a className="text-blue-700 text-sm underline" href={audioSrc} download="summary.wav">Download audio</a>
        </>
      )}
      {!audioSrc && <div className="border border-dashed rounded p-3 text-center text-sm text-gray-500">Audio player placeholder</div>}
      {children}
    </div>
  )
}
