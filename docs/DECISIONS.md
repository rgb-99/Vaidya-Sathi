# Decisions Log

> Running log of technical choices made during development.
> Each entry records what was decided, why, and when.

---

## Format

Each entry follows:

```
### [DATE] — [Decision Title]
**Choice:** ...
**Alternatives considered:** ...
**Reason:** ...
**Impact:** ...
```

---

### 2026-11-03 — STT Mode

**Choice:** TBD — will compare `transcribe` vs `codemix` on demo audio.
**Alternatives considered:** `transcribe`, `codemix`.
**Reason:** Need to test which mode extracts drug names and vitals more accurately from code-mixed Marathi/Hindi/English speech.
**Impact:** Set via `STT_MODE` env var; no code change needed to switch.

### 2026-11-03 — LLM Models

**Choice:** `sarvam-105b` for structuring, `sarvam-105b-conversations` for summary generation.
**Alternatives considered:** None — these are the current non-deprecated models.
**Reason:** PRD specifies these. `sarvam-m` and `saarika` are deprecated.
**Impact:** Set via `LLM_MODEL` and `LLM_MODEL_CONVERSATION` env vars.

### 2026-11-03 — TTS Model and Voices

**Choice:** `bulbul:v4-flash`. Speaker names TBD — need to verify from docs.
**Alternatives considered:** None — this is the current model.
**Reason:** PRD specifies this model.
**Impact:** Set via `TTS_MODEL`, `TTS_SPEAKER_MR`, `TTS_SPEAKER_HI`, `TTS_SPEAKER_EN` env vars.

### 2026-11-03 — Extraction Prompt Version

**Choice:** v1 — initial extraction prompt as specified in TRD section 8.1, with 2 few-shot examples from S1 and S2.
**Alternatives considered:** None yet.
**Reason:** Starting point per the spec.
**Impact:** Prompt versions tracked in provenance metadata (F25).

### 2026-11-03 — Model Fallback Strategy

**Choice:** TBD.
**Alternatives considered:** Retry once, then return empty record with warning.
**Reason:** Per TRD section 7.2 — on second LLM failure, return empty form so doctor can type manually.
**Impact:** User sees a warning but can still use the app.


### 2026-11-03 — M0 scaffold choices

**Choice:** Tailwind v3 with PostCSS; Python venv at `.venv/` (git-ignored); frontend dev server proxies `/api` and `/demo` to port 8000; MOCK_MODE is set via environment variable when running mocks so `.env` can keep `MOCK_MODE=false` for real calls.
**Alternatives considered:** Tailwind v4 plugin; system Python.
**Reason:** v3 is the stable, widely documented setup. The proxy avoids CORS during development (CORS is still configured from `CORS_ORIGIN`).
**Impact:** No extra dependencies beyond the spec. `httpx` was deliberately not added, so route behaviour is checked with curl and the schema with pytest.

### 2026-11-03 — M0 mock behaviour

**Choice:** Mock routes pick a scenario from the upload filename (`S1`/`S2`/`S3`, default S1), from an exact transcript match, or from the first drug of a record. `/redflags` in mock mode only returns S2's canned flags when S2's vitals are present. Routes not implemented for real return 501 when `MOCK_MODE=false`; `/referral` returns 400 before 501 when `confirmed` is not true.
**Reason:** Keeps the full UI clickable offline. The real rule engine is M4 and must stay deterministic.
**Impact:** Canned summaries and alert text in Marathi and Hindi were written without native-speaker review. Treat them as placeholders. `demo/audio/mock.wav` is a generated tone, not speech.

### 2026-11-03 — Smoke test goes through sarvam_client

**Choice:** `scripts/smoke_sarvam.py` calls `sarvam_client.chat()` rather than importing `sarvamai`.
**Reason:** CLAUDE.md makes `sarvam_client.py` the only file that imports `sarvamai`.
**Impact:** The smoke test also exercises config loading and error mapping. Result: reply received from `sarvam-105b-conversations`.

### 2026-11-03 — M1: STT_MODE = codemix (provisional)

**Choice:** `STT_MODE=codemix` in `.env.example` (and local `.env`), on `saaras:v4`.
**Alternatives considered:** `transcribe`.
**Evidence** (`python scripts/compare_stt.py`, 3 synthetic Bulbul clips of 9 to 20 s, language auto-detected correctly as mr-IN, mr-IN, hi-IN in both modes):

| mode | mean WER | drug names exact | numbers exact | mean latency |
| --- | --- | --- | --- | --- |
| transcribe | 0.34 | 0/3 | 6/9 | 1.0 s |
| codemix | 0.27 | 3/3 | 6/9 | 0.8 s |

Per clip WER: S1 transcribe 0.45 vs codemix 0.18; S2 0.38 vs 0.45 (transcribe better); S3 0.20 vs 0.19.
**Reason:** `transcribe` writes drug names in Devanagari (मेटोप्रोलोल, मेटफॉर्मिन), `codemix` keeps them in Latin script (Metoprolol, Metformin), which is what the formulary fuzzy match (TRD 7.4) and the safety checks need. Latency was the same within noise.
**Caveats (do not quote these as accuracy numbers):**
- The clips are synthetic TTS audio, cleaner than a real clinic microphone, and n=3, so differences are indicative only. The pitch must not quote them.
- The references use Latin script for drug names, so WER partly measures script choice, not hearing. The drug-name column is the more meaningful signal.
- **Finding for M2/M4:** in S2 both modes write spoken numbers as words (`एकशे दोन`, `नव्वद बाय साठ`, `एकशे अठरा`), so 0/3 numbers matched. The structuring step must convert number words to digits before red-flag rules run. Both modes behave the same here.
**Impact:** Re-run `compare_stt.py` on real fake-patient recordings (same filenames in `demo/audio/`) before the demo and revisit this decision. Switching needs only the env var.

### 2026-11-03 — M1: audio handling

**Choice:** `voice.transcribe()` works in a `TemporaryDirectory` (deleted on return, success or error). Accepted formats with a known duration of 30 s or less go to Sarvam unchanged. Browser WebM has no duration header (ffprobe reports N/A), so unknown-duration, unaccepted and longer files are decoded to 16 kHz mono WAV with ffmpeg. Audio over 30 s is split into chunks of at most 28 s, cut at the latest silence (ffmpeg `silencedetect`, -35 dB, 0.3 s) in the window, hard cut if none. Chunk transcripts are joined with spaces and the most common detected language is returned.
**Alternatives considered:** Batch API (needs job polling, better suited to diarization in M8); fixed-length cuts (can split words).
**Errors:** unreadable file or empty upload 400, over `MAX_AUDIO_SECONDS` 413, missing ffmpeg 500, Sarvam failure 502 with a friendly message. 429 and client timeouts are retried once with 2 s backoff.
**Impact:** Requires `ffmpeg` and `ffprobe` on the server (system packages, not pip). Verified live: browser-style WebM (200), a 66 s clip split into 3 requests (200), garbage file (400).

### 2026-11-03 — M1: stand-in demo clips

**Choice:** `demo/audio/S1-S3.wav` are synthetic (Bulbul), generated by `scripts/synthesize_demo_clips.py` from `demo/transcripts/*.txt`. TTS voices used were verified against the live API. See `demo/README.md`.
**Reason:** No real recordings existed. They must be replaced with fake-patient recordings for honest measurements.

### 2026-11-03 — UI visual language

**Choice:** Restyled the frontend after the look of sarvam.ai: off-white canvas (`#fafafa`), near-black ink (`#131313`), one indigo accent (`#2b2bb8`), hairline borders (`#e6e6e6`), rounded cards, pill buttons, mono uppercase step labels (`01 — Record`). Tokens live in `frontend/tailwind.config.js` and `frontend/src/index.css`.
**Alternatives considered:** Copying their fonts, logos and illustrations (not done: custom licensed fonts and Sarvam's brand assets).
**Reason:** Matches the event sponsor's look without impersonating them. System fonts only, so the app still works offline in MOCK_MODE.
**Impact:** Styling only, no logic change. Red and amber red-flag colours are kept for safety meaning. The safety label is a permanent black strip under the header.

### 2026-11-03 — M2: extraction prompt v1 and eval

**Choice:** Prompt `v1` = SPEC 8.1 text + two few-shot examples (S1, S2 mock transcripts; S3 held out) + one added line: write spoken numbers as digits ("एकशे दोन" -> 102, "नव्वद बाय साठ" -> 90/60), because STT writes numbers as words (see M1). Model `LLM_MODEL` (sarvam-105b), temperature 0, max_tokens 4096. Fences and `<think>` blocks stripped; one retry with the validation error appended; then an empty record with `warnings` set. The LLM's `red_flags` output is always discarded; red flags only come from `redflags.py` (M4). Drug names normalized with rapidfuzz (cutoff 85) against ~40 formulary names. Added `warnings: List[str]` to `ClinicalRecord` (additive) to carry the visible failure warning. Mock expected records no longer contain facts the transcripts never state (patient names, diagnoses).
**Eval** (`RUN_LIVE=1 pytest tests/test_structure_eval.py -s`; 4 inputs from demo transcripts, S2 also as number words): **26/27 fields = 96%, zero invented drugs**. One miss: S3 `vitals.sugar` ('180' not extracted). Small sample; the M9 harness gives the real numbers.
**Impact:** `/api/structure` is real when MOCK_MODE=false; red flags stay empty there until M4.

### 2026-11-03 — M3: summary and speech

**Choice:** `summarize()` uses `LLM_MODEL_CONVERSATION`, temperature 0.2, SPEC 8.2 prompt plus lines to keep drug names and doses in Latin letters and every other word in the target language. Post-check (machine): every prescribed drug present; no other formulary drug (word-boundary match); doses present and no extra doses; at most 120 words; no OD/BD/TDS/SOS style abbreviations. Regenerate once, then the template fallback (fixed phrase dictionary for mr, hi, en; free-text words not in the dictionary stay as the clinician's English). For Indic languages a leftover English closing sentence is replaced by the fixed translated "go to the hospital" sentence. `speak()` splits on sentence boundaries (2,000 chars, limit is 2,500) and joins WAVs. `/api/summary` returns 400 unless `confirmed: true` (added to the request; M7 replaces this with server-side sign-off); a TTS failure returns the text plus `audio_error` so the UI shows a Retry. Tablet counts ("one tablet") are not machine-checked; the clinician reviews the text.
**Voices:** mr `ishita_mr_conversational`, hi `kavya_hi_conversational`, en `ritu_en_medical`. They work with the API but I could not listen to them; the user must audition and change `TTS_SPEAKER_*` if needed.
**Live check (S1):** all three languages passed the post-check without fallback; audio 16 to 18 s (the spec target of 20 to 40 s is not reached; the text is short).

### 2026-11-03 — M4: deterministic red flags

**Choice:** `redflags.py` implements the 8 SPEC section 9 rules in pure Python; both `/api/structure` and `/api/redflags` use it (also in MOCK_MODE, since it needs no network). Keywords in English, romanized Hindi/Marathi and Devanagari; Latin keywords match on word boundaries. `/api/structure` stores the transcript in `record.utterances` so a later `/api/redflags` call (contract: body is the record) still sees symptom keywords after the clinician edits vitals. Alert audio uses fixed text per rule and language (SPEC 8.4), spoken with `voice.speak`.
**Conflict resolved:** SPEC table says RF_HYPOTENSION is systolic < 90, but S2 (BP 90/60) must trigger it per SPEC section 12, CLAUDE.md quality gates and the demo runbook. Used `<= 90`; flagged in `docs/SAFETY.md` for clinician review.
**Verified:** 111 tests pass (S2 -> SEPSIS + HYPOTENSION; S1, S3, empty -> none; boundaries). Live: STT-style number words -> LLM digits -> rules -> flags, edit to BP 120/80 drops HYPOTENSION, Hindi alert audio returned.

### 2026-11-03 — M7: sign-off, said vs inferred, audit trail

**Sign-off:** `POST /api/signoff {record, clinician_name}` sets `signed_off_by`, `signed_at` and `signature` (HMAC-SHA256 over the record, key generated on first use in `data/signing.key`, git-ignored) and saves the record to history. `signed_at` is set only there. Summary, referral and export verify the signature server-side (403 otherwise), so a forged or edited-after-signing record is rejected. Derived fields (`red_flags`, `safety_warnings`, `warnings`) are outside the signature so live red-flag recompute is unaffected. The old `confirmed` flag on `/api/summary` and `POST /api/records` were replaced by sign-off. Share link will use the same gate in M10. Caveat: the key lives next to the DB, so this is integrity for a demo, not a hardened trust boundary.
**Said vs inferred:** prompt `v2` asks for `evidence[{field, quote}]`. The machine, not the LLM, decides: a value is `said` only if its quote is a verbatim substring of the transcript (whitespace, case and Devanagari digits normalized); otherwise the sentence that literally contains the value is used; otherwise the value is listed as `Unverified, no matching quote` in `inferred` (right column, labelled AI-suggested, not verified). No timing link: the STT call does not request timestamps, so facts link to the transcript quote and its offset, not to audio time.
**Audit trail:** `provenance[field]` = source utterance id (`u1`, the whole transcript), model, prompt version, quote, offset. `GET /api/export/{id}.json` returns a FHIR-inspired bundle (Patient, Encounter, Observation, MedicationRequest, each with an `audit` list). It is labelled "FHIR-inspired export. Not FHIR-compliant. No ABDM compliance claim."
**Problem found and fixed:** with prompt v2 the reasoning model used all 4,096 tokens thinking (`finish_reason=length`, empty content, 41 s), so every extraction failed and showed the empty-record warning. `reasoning_effort=None` (documented way to disable thinking) fixes it: 3 s, same accuracy. `structure()` now sets it. The summary call still uses default reasoning and works; revisit if it ever returns empty.
**Eval after v2:** 26/27 fields = 96%, zero invented drugs (unchanged); 132 tests pass.
