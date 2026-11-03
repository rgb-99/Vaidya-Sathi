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

### 2026-11-03 — M8: diarization, key terms, language breadth

**Diarization (F18):** available for `saaras:v4` but only through the Batch API (the REST endpoint has none). `sarvam_client.stt_diarized()` runs one job per recording; `voice.transcribe()` uses it when `ENABLE_DIARIZATION=true` (default off: it adds about 10 s) and falls back to the plain REST path with a visible notice if the job fails. Roles: `assign_roles()` scores each speaker by drug names (x3), doses and instruction words; the top scorer is the clinician, others the patient; one speaker or a tie leaves every turn `unknown` and the role-free prompt is used. `llm.structure()` labels turns Clinician/Patient and appends the role rules to the prompt. Because an LLM can ignore a rule, `enforce_clinician_orders()` then drops any prescribed drug that does not appear in a clinician turn (fuzzy match 85) and adds a visible warning, so a patient-only drug cannot reach the prescription. Known limit: a drug the clinician names only in Devanagari script (non-codemix STT) would be dropped with that warning. The UI shows coloured turns and a Swap roles button; editing the transcript text discards the turns. Provenance now points at the utterance that contains each quote. Live: a 2-voice clip (patient asks about Aspirin, clinician prescribes Metoprolol) gave patient/clinician/patient turns and a prescription of Metoprolol only.
**Key terms (F19):** `ENABLE_KEYTERMS=true` passes the 40 formulary names as `keyterms` (limit 50 terms x 64 chars, checked by a test). `scripts/keyterms_report.py` on S1 to S3: drugs 3/3 both with and without, mean WER 0.27 both. **No improvement shown, so none is claimed;** the flag stays off. Synthetic, clean clips only; real noisy audio may differ.
**Languages (F29):** `GET /api/languages` lists the 9 languages with a live-API-verified voice (mr, hi, en, bn, gu, kn, pa, ta, te). Bulbul also lists ml-IN and od-IN, but no voice name was accepted, so they are not offered. The summary prompt works in any of them; the fixed-phrase template fallback exists only for mr, hi, en, so for the other languages a failed safety check falls back to an English template spoken with the English voice (the response `language` says so). Detected STT language selects the summary language unless the user picked one manually. The extra voices were API-accepted but not auditioned.
**Tests:** 149 pass.

### 2026-11-03 — M9: evaluation harness

**Built:** `eval/build_scenarios.py` generates `eval/scenarios.jsonl` (32 synthetic scripts: 14 visits incl. multi-drug, 10 red-flag cases, 4 noisy and 4 fast variants; Marathi, Hindi, English; none overlap the prompt's few-shot examples; a test checks every expected drug, dose and vital is stated in the script). `eval/synthesize_audio.py` (Bulbul, one voice per role, noise at 10 dB SNR, fast = pace 1.4) prints its API-call estimate and does nothing without `--yes`. `eval/run_eval.py --all` computes per-field F1, drug and dose exact match, hallucinations, red-flag precision and recall, speaker accuracy and key-term A/B (audio mode only), p50/p95 latency per stage. `eval/report.py` writes the reports and the regression gate. `GET /api/eval/latest` and an Eval tab show the latest run against the previous one.
**First real numbers** (text mode, 32 scenarios, run in `eval/reports/latest.json`): overall F1 95.6%, drug 100%, dose 100%, red-flag precision and recall 100%, 0 hallucinations, 0 extraction failures, structure() p50 4.2 s.
**Scorer calibration (disclosed):** the first run scored 90.1% because "Eat less salt" did not match the expected "low salt" and "dizziness" did not match "giddiness". Those were correct answers rejected by the metric, so advice is now matched on a key word and a synonym list was added. This changed the evaluator only, not the pipeline, and the F1 rise from 90.1 to 95.6 is mostly that.
**Real model failure found (proposal, NOT applied; waiting for approval per the playbook):** about 1 in 32 times the model keeps complaints, advice, timing and follow-up in the source script (Marathi) instead of English. Same input, temperature 0, different outcome across runs (F01 first, E03 second).

| # | Proposed change | Expected effect | Risk |
| --- | --- | --- | --- |
| 1 | Add to the prompt: "All string values in the JSON must be in English, even if the transcript is in another language (except drug names)." plus one few-shot example whose transcript is Marathi and whose output is English | Removes most untranslated outputs | Small prompt growth; must re-run the eval and check hallucinations stay 0 |
| 2 | Deterministic check after extraction: if a complaint, advice or timing string contains non-ASCII letters, retry once with an explicit "translate to English" message | Catches the remaining cases | One extra LLM call on about 3% of requests |
| 3 | Use `response_format=json_object` | Fewer fence and format issues | Does not address translation; not needed now |

**Not done yet (waiting for your review of `eval/scenarios.jsonl`):** audio synthesis. Estimate for all 32 scenarios: 80 Bulbul calls (one per turn), then each audio-mode eval run adds 32 STT calls and 32 LLM calls (plus 32 batch jobs with `--diarize`, and 64 more STT calls with `--keyterms-ab`).

### 2026-11-03 — M10: share page, reminders, safety checks

**Share (F22):** `POST /api/share` requires sign-off, summarizes and speaks once at creation, and stores only the public payload (first name, schedule, advice, follow-up, summary text, audio, diagnosis only if ticked, expiry) in the `shares` table, so the public endpoint cannot leak anything else by construction. Token = `secrets.token_urlsafe(16)` (128 bits). `GET /api/share/{token}`: 404 unknown or expired, 429 over 30 requests a minute per client (in-memory), `X-Robots-Tag: noindex, nofollow`, `Cache-Control: no-store`. QR PNG generated server-side with `segno` (approved by the user; no dependencies of its own). The public page is the frontend route `/share/<token>` (large print, morning/afternoon/evening-night icons, Play again). Limits: the in-memory rate limiter resets on restart and is per process; the QR link uses `PUBLIC_BASE_URL`.
**Reminders (F23):** `GET /api/schedule.ics?record_id=` (signed records only). One daily event per medicine and column time (08:00, 14:00, 20:00 floating local time), repeated for the prescribed duration; no duration means no repeat, and medicines with no stated time of day go at 09:00 with a note; nothing is invented.
**Safety checks (F24):** `safety.py` + `safety_rules.json` (duplicate drug, same-class for beta blockers, ARBs, statins, PPIs, allergy match; dose-limit table empty). `/api/structure` and `/api/safety` return warnings; the form recomputes on edits; allergies are typed by the clinician. `PRODUCTION_MODE` hides unreviewed rules. All rules have `reviewed_by` blank in `docs/SAFETY.md`.
**Tests:** 182 pass (share expiry and 404, no diagnosis or private-data leak, rate limit, ics validity and folding, one test per safety rule).

### 2026-11-03 — M11: prescription photos and reconciliation

**Reading (F15):** `vision.py` uses Document AI `extract` with a fixed JSON schema (medicines: drug, dose, frequency, duration). `POST /api/prescription-photo` validates the file (PNG, JPG, PDF; 10 MB our own limit), starts a background job and returns a job id; `GET /api/prescription-photo/{job}` returns status, items and error. The job store is in memory (lost on restart; images are never written to disk). Polling backs off from 1 s to 5 s and gives up after 90 s (504-style message). A payload with no usable medicine raises an error instead of returning an empty list, so "unreadable" is never shown as "no drugs". Drug names are normalized with the formulary. `ENABLE_VISION` gates the routes (503 when off); `.env` has it on, `.env.example` keeps it off. Mock mode returns canned items per sample name.
**Reconciliation (F26):** `POST /api/reconcile {record, previous}` is deterministic Python: drugs matched through the formulary; dose compared with spaces ignored; statuses new, stopped, dose_changed, unchanged, each with the photo's read confidence (min over fields; below 70% is flagged in the UI). The clinician can mark each line accepted or rejected, which only records the review: nothing is merged into the prescription.
**Samples:** `demo/prescriptions/rx1-rx3.png`, synthetic (see its README).
**Tests:** 203 pass (polling, timeout, failed job, malformed payloads, file validation, gating, mock, every diff case).

### 2026-11-03 — M9 audio-mode results and proposed fixes (not applied)

Run `20261103T144437Z`, audio mode, diarization on, 32 synthetic scenarios (see `docs/EVAL.md`): overall F1 91.5, drug 96.8, dose 58.1, red flags 100/100, hallucinations 0, speaker accuracy 88.9, STT p50 10.8 s / p95 28.5 s. Text mode was 98.8, so STT cost about 7 points.

| # | Finding | Proposed change | Expected effect | Risk |
| --- | --- | --- | --- | --- |
| 1 | STT writes "500 milligram" / "1 milligram"; extraction keeps it, scores as a dose miss, and `check_summary` only recognizes mg, mcg, g, ml so those doses go unchecked | Deterministic dose normalizer after extraction (milligram(s) -> mg, microgram(s) -> mcg, gram -> g, drop the space between number and unit); extend the summary post-check to the same units | Dose exact match 58% -> about 100% and the summary check covers every dose | "Exactly as spoken" in the SPEC is relaxed to a canonical unit form; needs your yes |
| 2 | STT misheard a drug (Glimepiride -> Glycopyrrolate, E06); nothing flags it | Flag any prescribed drug that is not in the formulary list as "not in the demo formulary, verify the name" (warning only) | Wrong drugs become visible to the clinician | False alarms for real drugs outside the 40-name demo list |
| 3 | STT p95 28.5 s with 4 parallel batch jobs | Re-measure with workers=1; use diarization only when asked | Honest single-consultation latency | None |
| 4 | Key terms: 29 vs 28 of 31 | None; keep off by default | | |

### 2026-11-03 — M12 (1/4): real-time streaming (F20)

**Built:** `WebSocket /api/stream?language=&scenario=` relays 16 kHz mono WAV chunks (about 1 s, binary) from the browser to Sarvam streaming STT through `sarvam_client.stream_relay` (the only SDK import) and sends back `{type: partial, text}` per segment, then `{type: done, transcript}`. Audio is never stored. Gated by `ENABLE_STREAMING` (off in `.env.example`, on in the local `.env`); the batch recorder stays the default and the fallback, and the UI says so when streaming is off. The relay flushes every 2 chunks and uses `high_vad_sensitivity`, because without flushing nothing arrived until the end of the audio. Mock mode streams canned words with no network. The browser side (`frontend/src/stream.js`, "Record live" button) appends words as they arrive and re-runs extraction at most every 4 s, then once more on stop.
**Measured** (`scripts/stream_check.py`, clips streamed at real-time pace, final record compared with the batch path): first words after **0.8 s (S1), 1.3 s (S2), 5.8 s (S3, Hindi)**, so "about 2 s" held for two of three clips. Final record vs batch: S1 4/4 facts, S2 4/4, S3 2/3, the difference being the dose written as "500मिलीग्राम" instead of "500mg" (the unit-normalization issue in the M9 proposal table, not a streaming error). Streaming transcripts are choppier (sentence fragments, numbers as words) and the extraction prompt handled them.
**Not verified:** the browser microphone path (`stream.js`, ScriptProcessor at 16 kHz) was written but not run in a real browser; the server relay was exercised with recorded clips only.
**Tests:** 207 pass (mock relay, disabled flag, relay with a fake Sarvam, Sarvam failure mid-stream). Found and fixed a hang: the mock relay waited for a message after `end`.

### 2026-11-03 — M12 (2/4): offline-first capture (F27)

**Built:** PWA manifest, SVG icon and a service worker (`frontend/public/`) that caches the app shell (network first, cache fallback; `/api` and `/demo` are never cached, so no patient data is cached). Registered only in production builds. Recordings made while `navigator.onLine` is false are stored in IndexedDB (`offline.js`) with a client-generated UUID and a status shown per item: queued, syncing, done, failed. "Sync now" and the browser `online` event call `POST /api/sync` (multipart `client_id` + `audio`) one item at a time. The server is idempotent: the first transcript for a `client_id` is stored in SQLite (`sync_results`, transcript only, never audio) and any repeat returns it with `duplicate: true` without calling Sarvam; failed transcriptions are not stored, so a retry can succeed. Ids are validated (`[\w-]{8,64}`). When an item syncs, the audio blob is dropped from the device and the transcript stays until "Use transcript" or Delete.
**Verified:** 217 tests (including repeat, retry-after-failure and invalid ids); live with the real STT: first call 1.0 s, repeat 3 ms and `duplicate: true`, one transcription only. The production build contains manifest, icon and `sw.js`.
**Not verified:** the service worker, installability and the IndexedDB flow in a real browser, including going offline and back; no browser automation was run. Known limits: the shell is only cached after one online visit, there is no PNG icon (SVG only), and extraction and every later step still need the network.

### 2026-11-03 — M12 (3/4): PII masking before the LLM (F28)

**Built:** `masking.py` replaces names, phone numbers and 9+ digit runs with `<NAME_n>`, `<PHONE_n>`, `<ID_n>` before the extraction call and restores the tokens in the parsed output (also on the retry message). The map is a per-request object, never stored. Evidence quotes are then checked against the original transcript, not the masked one. Clinical numbers (BP, pulse, doses, durations) are not touched. `ENABLE_PII_MASKING` is on by default. Summaries never receive names (their payload is diagnosis, prescription, advice, follow-up only).
**Honest limits:** names are found only by cue words ("my name is", "Mr./Mrs./Smt./Shri", "नाव", "नाम", "श्री") or when the caller passes `known_names`; a name spoken with no cue word is not detected (no name-recognition model, and none was added). Unusual number formats may slip through. Masked text still reaches Sarvam's STT: audio is not masked.
**Bug found by the live check and fixed:** the name token swallowed the trailing "है।" (Devanagari danda matched as a letter; only the first word was checked against stop words), so the record's patient name came back as "सुनीता देशमुख है।". Now trailing grammar words and the danda are excluded.
**Evaluation after the change** (text mode, 32 scenarios, `--no-latest` so the committed audio report is untouched): overall F1 99.4 (was 98.8), drug and dose 100, hallucinations 0, **red-flag recall 92.9 (was 100)**. The drop is one scenario, R05 (hypoxia): the model did not extract "ऑक्सीजन 88" on that run although masking did not alter the text and it succeeded in earlier runs, so this is run-to-run model variance, but a missed SpO2 is a missed hypoxia alert. It reinforces the clinician review step, and a candidate for a future retry rule (for example re-ask when a vital word such as "ऑक्सीजन" is in the transcript and `spo2` is empty); not applied.
**Tests:** 243 pass (token types, clinical text untouched, nested restore, the model input contains no private details, retry is masked, evidence uses the original text, off switch).

### 2026-11-03 — M12 (4/4): clinician analytics (F30)

**Built:** `analytics.py` + an Analytics tab. At sign-off the server stores one `consultations` row: start time (sent by the browser: the moment the transcript became available), sign-off time, measured seconds, whether it came from the demo picker, language, red-flag and urgent counts, safety warnings. The typing baseline (minutes) is entered once and stored in `settings`. **Minutes saved = baseline minus measured documentation time**, over live consultations that have a measured time; demo runs, runs with no start time and implausible durations (negative or over 4 h) are never included, and with no baseline or no measured run the panel says "not measured" instead of showing a number. A slower-than-baseline run shows as negative savings. Red-flag, warning and language counts cover every signed-off consultation.
**Limits:** the start time comes from the browser clock; the figure measures time with the tool (transcript ready to sign-off), not the length of the consultation or recording; the baseline is the clinician's own estimate. The analytics table was added to the existing SQLite file.
**Tests:** 252 pass (nothing measured, baseline required, demo and unmeasured exclusion, implausible durations, counts, negative savings, baseline validation).

### 2026-11-03 — M13: definition-of-done audit (SPEC sections 17 and 19)

Evidence is a test, a command output or a measured run. "Not verified" means I could not do it from the terminal.

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| 17.1 | Fresh clone runs with MOCK_MODE=true, no key | Met | Cloned the repo into a temp folder, followed the README, 252 tests passed, backend and frontend started, full mock flow (transcribe, structure, sign-off, summary, alert audio, referral, share, export, ics, card) returned 200s |
| 17.2 | With a key, S1, S2, S3 end to end under 20 s each | **Partly** | Audio to filled record 11.9, 3.7, 5.5 s. To a spoken summary 20.5, 11.1, 18.1 s, so S1 is 0.5 s over (STT time varies: S1 took 1.5 s in an earlier run). Single run each |
| 17.3 | All tests pass; eval at 90% or above | **Partly** | 252 pass, 1 skipped (live eval, opt-in). Overall F1 90.9% in the final audio run (91.5% before; text mode 98.8 to 99.4%), but the harness regression gate FAILED on the final run (drug exact 96.8 to 93.5, speech-model variation) and dose exact match is 58.1% |
| 17.4 | Red-flag banner correct on S2 and absent on S1 | Met in code, UI not viewed | `test_redflags.py`; live API on S1 to S3 (S2: SEPSIS + HYPOTENSION; S1, S3: none). I did not look at the banner in a browser |
| 17.5 | Safety label visible; no invented drugs in any output | Met (label seen once in a screenshot) | Header strip in every view; 0 hallucinations in 3 evaluation runs; summary post-check tests. The summary check does not recognize doses written in words ("500 milligram"): see the M9 proposal |
| 17.6 | README documents run steps, env vars, models, limits | Met | README |
| 19.1 | 30+ scenarios, zero hallucinations, /eval page renders | Met (page not viewed) | 32 scenarios; `/api/eval/latest` returns the report; component builds |
| 19.2 | Diarization labels visible and swappable; patient-only drug never in the prescription | Met in code and live API, UI not clicked | `test_m8.py`, live two-voice clip |
| 19.3 | Share page works on a phone, no login, schedule and audio, expires | API met, phone not verified | `test_m10.py` (expiry 404, no leaks, rate limit); not opened on a phone |
| 19.4 | Sign-off required before share, summary audio, export, referral | Met | `test_m7.py`, `test_m10.py`, live 403 on unsigned |
| 19.5 | Safety checks fire on duplicate, same class, allergy, each tested | Met | `test_m10.py` one test per rule |
| 19.6 | Offline capture queues and syncs without duplicates | Server met, browser not verified | `test_sync.py`, live duplicate check; IndexedDB queue and service worker never run in a browser |
| 19.7 | Advanced features degrade gracefully, UI says what is off | Mostly met | Diarization failure falls back with a notice; streaming off returns a message; TTS failure shows the text with Retry; vision off hides the upload (the UI does not say why); mock mode everywhere |

**Security pass:** key pattern searched in the whole tree and every commit: none. `.env` ignored and untracked. CORS limited to `CORS_ORIGIN`. Share tokens are 128-bit and expire. Tracked audio and images are all synthetic. No real PII. The key you pasted into the chat is only in your local `.env`; rotate it.
**Left for you (needs a human):** listen to the voices in all three main languages; click through mic recording, live transcription, offline mode, printing and the share page on a phone; have a clinician review the rules and the Marathi and Hindi alert texts; decide on the proposed dose normalizer and the not-in-formulary warning.

### 2026-11-03 — UI: dark theme, full-screen layout, auto language

**Theme:** colours are CSS variables (`frontend/src/index.css`) used through Tailwind tokens (`bg-surface`, `text-ink`, ...), so every component follows the theme. Dark is the default; the header button switches and remembers the choice (`localStorage` key `vs-theme`; an inline script in `index.html` sets the class before first paint). Semantic boxes (red flags, warnings, sign-off) have explicit `dark:` variants. The safety label is an amber strip in both themes.
**Layout:** the consultation view is a viewport-height, full-width three-column grid (`capture | review (2.2x) | patient`) with no page scroll on desktop. The review column uses tabs (Record, Evidence, Prescription photo) and a compact form (prescription rows on one line), red-flag cards are one-line. Panels fall back to an inner scroll only if content is taller than the screen; below the `lg` breakpoint the page stacks and scrolls normally. History, Eval and Analytics also use the full width. Checked in headless Firefox through WebDriver BiDi with real clicks (S2 and S1, sign-off, summary, share): 1920x1080 and 1366x768 both fit with no page scroll and no inner scroll for a record with two medicines. Not checked: phone-width layout, other browsers, records with many medicines (they scroll inside the panel).
**Auto language:** the language selector now defaults to "Auto-detect". The language for the summary, alerts and share page follows what Saaras detected in the audio (or `language_detected` from the record when the transcript was typed); a detected language without a voice falls back to English, and so does a run where nothing could be detected (English); no regional language is ever assumed. Until a language is heard the panel says "language auto-detected". Picking a language by hand overrides it. The header shows the detected language, and the patient panel says "(auto)". Live streaming in auto mode sends `unknown` as the language: tested live, first words after 1.2 s.
**Note:** changing `tailwind.config.js` needs a restart of the Vite dev server (it keeps the old config in memory and then fails to compile the CSS).

### 2026-11-03 — UI: pure black theme, white buttons

Dark theme is now pure black (`--bg` and `--surface` `0 0 0`; the page and cards computed as `rgb(0, 0, 0)`), with thin grey borders (`52 52 56`) giving the structure, white text-on-black primary buttons (`--accent` white, `--on-accent` black via the `onaccent` Tailwind colour) and white links. The light theme keeps its indigo buttons. Needs a restart of the Vite dev server (Tailwind config changed).
