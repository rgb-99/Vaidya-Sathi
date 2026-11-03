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
