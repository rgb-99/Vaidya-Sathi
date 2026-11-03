# Vaidya Saathi

Ambient clinical documentation, red-flag triage support, and vernacular patient summaries. Built for Sarvam Campus x IIIT Pune '26.

---

## What It Does

A doctor or health worker simply talks. The app:

1. **Listens** to the code-mixed Marathi/Hindi/English conversation.
2. **Fills** the clinical record automatically.
3. **Flags** urgent red-flag risks using fixed protocol rules (not AI).
4. **Speaks** a simple medicine-schedule summary back to the patient in their own language.

> **AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.**

---

## Tech Stack

- **Frontend:** React (Vite) + Tailwind CSS
- **Backend:** Python 3.11 + FastAPI + Pydantic v2 + SQLite
- **AI:** Sarvam AI (Saaras STT, sarvam-105b LLM, Bulbul TTS)

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd vaidya-saathi
cp .env.example .env
# Edit .env and add your SARVAM_API_KEY
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Mock Mode (no API key needed)

```bash
# Set MOCK_MODE=true in .env, then start the backend
cd backend
uvicorn main:app --reload --port 8000
# All endpoints return canned data — full UI works offline
```

### 5. Sarvam Onboarding (verify your API key)

```bash
# From the repo root
python scripts/smoke_sarvam.py
```

> Status (M0): every `/api` route returns canned data in mock mode. With `MOCK_MODE=false`, routes not yet implemented for real return `501`. Real STT is M1.

---

## Environment Variables

See [`.env.example`](.env.example) for all variables. Key ones:

| Variable | Purpose |
|----------|---------|
| `SARVAM_API_KEY` | Your Sarvam AI API key |
| `MOCK_MODE` | `true` to run without network/API key |
| `STT_MODEL` | Speech-to-text model (default: `saaras:v4`) |
| `LLM_MODEL` | LLM for structuring (default: `sarvam-105b`) |
| `TTS_MODEL` | Text-to-speech model (default: `bulbul:v4-flash`) |

---

## Safety

Red-flag and safety rules in this project are **demo-grade screening rules for decision support**. They must be reviewed by a qualified clinician before any real-world use. This tool is **not a substitute for medical judgement**.

- Red flags come from deterministic rules, not AI.
- The patient summary only restates what the clinician prescribed.
- Human confirmation is required before generating summary audio or referral tickets.
- All demo data is fake. No real patient information is used.

---

## Documentation

| File | Purpose |
|------|---------|
| [`docs/SPEC.md`](docs/SPEC.md) | Full PRD + TRD (source of truth) |
| [`docs/SARVAM_NOTES.md`](docs/SARVAM_NOTES.md) | Sarvam API reference |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Technical decisions log |
| [`docs/SAFETY.md`](docs/SAFETY.md) | Safety rules and review status |
| [`docs/EVAL.md`](docs/EVAL.md) | Evaluation harness guide |
| [`docs/DEMO.md`](docs/DEMO.md) | Demo runbook |
| [`docs/PITCH.md`](docs/PITCH.md) | Pitch slide text |
| [`docs/SOURCES.md`](docs/SOURCES.md) | Citation tracker |

---

## License

For hackathon use only.

