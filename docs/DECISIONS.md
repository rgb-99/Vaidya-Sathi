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
