# Vaidya Saathi — Rules for Claude Code

> Read this file before writing any code. These rules are non-negotiable.

## Source of Truth

`docs/SPEC.md` is the single source of truth (PRD + TRD). Build exactly what is specified. Do not add auth, payments, databases beyond SQLite, or features not listed.

## Build Order

Follow the milestones in TRD section 14. Complete each milestone and make it run before starting the next:

1. **M0 (setup):** repo, env, FastAPI health check, Vite app, schemas.py, mock_data.py with 3 scenarios, MOCK_MODE end to end returning canned data. App fully clickable with mocks.
2. **M1 (STT):** real `transcribe()`. Test on recorded S1 audio. Compare model options.
3. **M2 (structuring):** real `structure()` with prompt, validation, retry, formulary. Pass the eval at 90%.
4. **M3 (summary + TTS):** `summarize()` with post-check and template fallback, `speak()`, audio player in UI.
5. **M4 (red flags):** rules, tests, banner, alert audio.
6. **M5 (polish and demo):** DemoPicker, error states, README, record backup audio, rehearse.
7. **M6 (stretch):** referral ticket, history, printable card.

After each milestone: run tests, commit, and confirm the app still starts.

**Extended milestones (after M0–M6 are solid):**

- **M7:** clinician sign-off (F14), said-vs-inferred summary (F13), audit trail (F25).
- **M8:** speaker diarization (F18), key-term boosting (F19), language breadth (F29).
- **M9:** evaluation harness (F21). Build this before further prompt tuning.
- **M10:** patient share page with QR (F22), reminder calendar file (F23), prescription safety checks (F24).
- **M11:** prescription photo reading and reconciliation (F15, F26), referral ticket and record history.
- **M12:** real-time streaming (F20), offline-first capture (F27), PII masking (F28), analytics (F30).
- **M13:** polish, demo mode, rehearsal, README, final evaluation run.

## Sarvam API Rules

- Before writing any Sarvam API code, read the current official docs at https://docs.sarvam.ai (speech-to-text, text-to-speech, chat completions).
- Install: `pip install -U sarvamai`
- Create a `.env` containing `SARVAM_API_KEY=` and add `.env` to `.gitignore`.
- **Never hardcode or print the key.**
- The first milestone is one chat call with `sarvam-105b-conversations`.
- If the key is missing, **STOP and ask the human to paste it** (no dummy values, no test requests without it).

### Verified API calls (from docs.sarvam.ai):

```python
# Chat
client.chat.completions(model=..., messages=[...])

# Speech to text
client.speech_to_text.transcribe(file=..., model='saaras:v4', mode='transcribe')

# Text to speech
client.text_to_speech.convert(language_code=..., text=..., model='bulbul:v4-flash', speaker=...)
# returns base64 WAV in `audios`
```

- **Deprecated (do not use):** `saarika`, `sarvam-m`.
- All model names live in environment variables so they can be changed without code edits.
- Anything not listed here must be read from the docs, never guessed.

## Mock Mode

Every external call (STT, LLM, TTS) must have a mock mode (`MOCK_MODE=true`) returning canned data, so the app runs with no network and no API key.

## Safety Rules

- **Never let an LLM decide red flags or doses.** Red flags come only from deterministic rules (TRD section 9).
- The patient summary may only restate what the clinician prescribed. It must not add new medicines, change doses, or give new advice.
- Human confirmation required before summary audio and referral tickets.
- Clear on-screen label: "AI-assisted documentation. Clinician must review. Not a substitute for medical judgement."

## Code Style

- Keep code minimal and readable. Prefer one file per module.
- Use only fake patient data. Never store real patient audio.
- Log each pipeline step with duration (no patient audio stored on disk beyond the request).

## Run Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend
pytest tests/

# Sarvam onboarding smoke test (first thing to run with a real API key)
python scripts/smoke_sarvam.py

# Mock mode (no API key needed — set MOCK_MODE=true in .env)
uvicorn main:app --reload --port 8000
```

## Key Files

- `docs/SPEC.md` — full PRD + TRD (read this first)
- `docs/SARVAM_NOTES.md` — Sarvam API reference
- `docs/DECISIONS.md` — log every technical choice here
- `docs/SAFETY.md` — safety rules and review status
- `backend/schemas.py` — Pydantic models (the data contract)
- `backend/sarvam_client.py` — the ONLY file that imports `sarvamai`

## Quality Gates

- After every milestone, run unit tests and confirm the app starts.
- Red-flag tests must pass: S2 triggers RF_SEPSIS and RF_HYPOTENSION; S1 triggers none.
- Eval target: ≥90% field extraction accuracy on 3 demo scenarios.
- Zero invented drugs or doses across test runs.

