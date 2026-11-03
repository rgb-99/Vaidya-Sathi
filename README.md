# Vaidya Saathi

Ambient clinical documentation, red-flag triage support, and vernacular patient summaries. Built for Sarvam Campus x IIIT Pune '26.

> **AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.**

A doctor or health worker simply talks. The app listens to the code-mixed Marathi/Hindi/English conversation, fills the clinical record, flags urgent danger signs with fixed rules (not AI), and speaks a simple medicine schedule back to the patient in their own language. All demo data is fake.

---

## Quick start (no API key needed)

Needs Python 3.11 or newer (developed and tested on 3.14) and Node 18 or newer.

```bash
git clone <repo-url>
cd vaidya-saathi
cp .env.example .env            # then set MOCK_MODE=true in .env

python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
uvicorn main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                     # open http://localhost:5173
```

Both at once: `./scripts/dev.sh` (Windows: `.\scripts\dev.ps1`). With `MOCK_MODE=true` every step returns canned data with no network, so you can pick **S1**, **S2** or **S3** in the demo picker and click through the whole flow (Record, Check, Patient). The header shows a MOCK badge.

## Using the real Sarvam APIs

1. Put your key in `.env` (`SARVAM_API_KEY=`), set `MOCK_MODE=false`. Never commit `.env`.
2. Install **ffmpeg** and **ffprobe** (system packages; used to decode browser audio and split clips over 30 s).
3. Check the key: `python scripts/smoke_sarvam.py` (from the repo root).
4. Start the app as above.

Optional features are switched by environment variable (see the table below): live transcription, speaker separation, prescription photos.

## Tests and evaluation

```bash
cd backend && pytest tests/                 # unit tests (no network needed)
RUN_LIVE=1 pytest tests/test_structure_eval.py -s   # live extraction check, needs a key

python eval/build_scenarios.py              # (re)writes eval/scenarios.jsonl (32 synthetic scripts)
python eval/run_eval.py --all               # text mode: LLM calls only
python eval/synthesize_audio.py --yes       # builds synthetic audio with Bulbul (prints the call estimate first)
python eval/run_eval.py --all --mode audio --diarize --keyterms-ab
```

The latest committed report is `eval/reports/latest.json` (also shown on the Eval tab). Results, definitions and caveats: [`docs/EVAL.md`](docs/EVAL.md). The evaluation is on **synthetic scripts and synthetic speech**, not real clinic audio.

---

## What is built

| Area | Features |
|------|----------|
| Capture | Browser microphone, file upload, demo clips, optional live transcription, offline queue that syncs later |
| Record | Transcript to structured record (schema validated, retry, formulary spelling fix), editable form, said-versus-inferred panel with transcript quotes |
| Safety | Deterministic red flags with the matched inputs, spoken alerts, prescription safety checks (duplicate drug, same class, allergy), PII masking before the language model |
| Control | Clinician sign-off enforced on the server before summary audio, referral, share link, export and reminder file |
| Patient | Plain-language schedule spoken in 9 languages, printable medicine card, share page with QR code, `.ics` reminder file |
| Records | Referral tickets and history in SQLite, FHIR-inspired JSON export with an audit trail, analytics of measured time saved |
| Extras | Speaker separation (clinician/patient), prescription photo reading and reconciliation, evaluation harness |

## What is not built or not verified

- **No real-clinic validation.** Everything was tested on synthetic scripts and synthetic speech.
- **Safety rules are unreviewed.** No clinician has reviewed the red-flag or prescription safety rules ([`docs/SAFETY.md`](docs/SAFETY.md)). The RF_HYPOTENSION threshold needed a decision (systolic 90 or below) and is flagged for review. The dose-limit table is deliberately empty.
- **Not tested in a real browser by the author:** microphone recording, live transcription, the offline queue and service worker, and the print dialog. The server sides of these were tested with recordings and unit tests.
- **Voices were not auditioned.** The text-to-speech voices were accepted by the API but nobody has listened to them. Malayalam and Odia are not offered because no voice name was accepted.
- **Speech recognition is imperfect.** On synthetic audio the model once heard one drug as another; the clinician's review is the safeguard. Handwriting recognition was only tried on printed text in a handwriting-style font.
- **PII masking is best effort.** Names are found by cue words ("my name is", "Mr.", "श्री"), not by a name model. Audio itself is not masked.
- **No accounts or login.** Sign-off records a typed clinician name, not an identity. Anyone with a share link can view it until it expires. Share rate limiting is in memory.
- **FHIR-inspired is not FHIR-compliant.** No ABDM or FHIR compliance is claimed.
- Not done: more voices and languages beyond the nine, real deployment hardening, clinician-reviewed rule sets.

## Environment variables

See [`.env.example`](.env.example). Model names live in variables so they can change without code edits.

| Variable | Purpose |
|----------|---------|
| `SARVAM_API_KEY` | Your Sarvam AI key (never printed or committed) |
| `MOCK_MODE` | `true` runs with no network and no key |
| `STT_MODEL`, `STT_MODE` | `saaras:v4`; mode `codemix` (chosen on 3 synthetic clips, see `docs/DECISIONS.md`) |
| `LLM_MODEL`, `LLM_MODEL_CONVERSATION` | `sarvam-105b` (extraction), `sarvam-105b-conversations` (summary) |
| `TTS_MODEL`, `TTS_SPEAKER_MR/HI/EN` | `bulbul:v4-flash` and one voice per language |
| `ENABLE_STREAMING` | `true` shows "Live (words as you speak)" under the microphone |
| `ENABLE_DIARIZATION` | `true` separates clinician and patient turns (Batch API, adds about 10 s) |
| `ENABLE_KEYTERMS` | `true` passes the drug list to the speech model (no measured gain, off by default) |
| `ENABLE_VISION` | `true` shows prescription photo reading |
| `ENABLE_PII_MASKING` | `true` (default) masks names, phones and long numbers before the language model |
| `PRODUCTION_MODE` | `true` ignores prescription safety rules that have no reviewer |
| `MAX_AUDIO_SECONDS`, `CORS_ORIGIN`, `PUBLIC_BASE_URL`, `SHARE_TOKEN_TTL_DAYS` | Limits, allowed origin, link base, share-link lifetime |
| `SIGNING_KEY` | Sign-off key shared by all server instances (hosting); empty locally, where `data/signing.key` is used |
| `VITE_API_BASE` (frontend, build time) | Backend origin when it is hosted apart from the frontend; empty in local dev (the Vite proxy is used) |

## Safety

Red-flag and safety rules in this project are **demo-grade screening rules for decision support**. They must be reviewed by a qualified clinician before any real-world use. This tool is **not a substitute for medical judgement**.

- Red flags and safety warnings come from deterministic, human-written rules, never from the language model.
- The patient summary only restates what the clinician prescribed; every drug and dose in it is machine-checked against the record, with a fixed template as the fallback.
- Summary audio, referral, share link, export and reminders require a verified clinician sign-off, checked on the server.
- All demo data is fake. Audio is processed in memory and not stored.

## Documentation

| File | Purpose |
|------|---------|
| [`docs/SPEC.md`](docs/SPEC.md) | Full PRD + TRD (source of truth) |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every technical choice, with measured results |
| [`docs/SARVAM_NOTES.md`](docs/SARVAM_NOTES.md) | Sarvam API details verified from the docs and live calls |
| [`docs/SAFETY.md`](docs/SAFETY.md) | Safety rules and review status |
| [`docs/EVAL.md`](docs/EVAL.md) | Evaluation guide and latest results |
| [`docs/DEMO.md`](docs/DEMO.md) | Demo runbook |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Hosting on Vercel (frontend + backend container) and its limits |
| [`docs/PITCH.md`](docs/PITCH.md) | Pitch text (numbers cite the evaluation report) |
| [`docs/SOURCES.md`](docs/SOURCES.md) | Where every number comes from |

## License

For hackathon use only.
