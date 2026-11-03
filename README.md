# Vaidya Saathi

**Talk. Check. Hand over.** A voice-first assistant for doctors and health workers in India: it listens to a consultation in code-mixed Marathi, Hindi and English, fills in the clinical record, flags danger signs with fixed rules, and reads a simple medicine schedule back to the patient in their own language.

Built on [Sarvam AI](https://www.sarvam.ai) speech and language models for Sarvam Campus x IIIT Pune '26.

**Live demo:** https://vaidya-saathi.vercel.app

> **AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.**
> All patient data in this project is fake. Do not enter real patient information.

---

## Contents

- [Why](#why)
- [Try it in one minute](#try-it-in-one-minute)
- [How to use](#how-to-use)
- [What it can do](#what-it-can-do)
- [Run it on your computer](#run-it-on-your-computer)
- [Deploy](#deploy)
- [Tests and evaluation](#tests-and-evaluation)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Environment variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Safety](#safety)
- [Documentation](#documentation)

---

## Why

In a busy clinic, doctors type while they talk, or skip the record altogether. Patients leave with a scribbled prescription they often cannot read, in a language that is not theirs. Vaidya Saathi lets the doctor simply talk: the app writes the record, points out danger signs, and gives the patient a spoken, plain-language schedule.

## Try it in one minute

1. Open https://vaidya-saathi.vercel.app (works on a phone or a laptop).
2. Under **Try a demo**, tap **S2: Rural PHC emergency**. A prerecorded consultation is transcribed.
3. Tap **Extract details**. A red **Danger signs found** banner appears (possible sepsis, very low blood pressure).
4. Type any doctor name in the bottom bar and tap **Sign and lock**.
5. Tap **Make summary**, then the big play button to hear the patient summary.

## How to use

The app is three screens, one after the other. The step bar at the top shows where you are; a step opens only when the one before it is done. Each screen has one main button at the bottom right.

### 1. Record

The first thing on screen is a large microphone button.

- **Tap the microphone** and talk with the patient as you normally would. The red ring moves with your voice so you can see it is listening. Tap again to stop (maximum 3 minutes).
- **Upload audio** sends a recording you already have (most audio formats work).
- **Type it instead** opens an empty box for typing or pasting the conversation.
- **Try a demo** plays one of three prerecorded consultations:
  - **S1**: hypertension follow-up in mixed Marathi, Hindi and English (two medicines, no danger signs).
  - **S2**: emergency at a rural health centre (fever, low blood pressure, fast pulse: two danger signs).
  - **S3**: diabetes follow-up, mostly Hindi.
- **Live (words as you speak)** appears only when live mode is switched on (`ENABLE_STREAMING=true`). Words show up while you talk and the details are filled in automatically when you stop.

After recording, the text appears under **What was said**. Fix any mistakes by tapping into it. If speaker separation is on, doctor and patient turns appear as chat bubbles; **Swap doctor / patient** fixes the labels if they are the wrong way round.

Tap **Extract details** to continue.

### 2. Check

The app reads the conversation and fills in the record (a few seconds).

- **Danger signs** appear first, in red (urgent) or amber (warning), each with the reason, for example "Because: temp 102F, BP 90/60, pulse 118". **Play alert** speaks the warning aloud in the selected language.
- **Check these medicines** (amber) appears when two medicines are the same, are from the same drug class, or match an allergy you entered. Nothing is changed automatically.
- The record is shown in plain sections: **Patient**, **Vitals**, **Medicines**, **Complaints**, **Advice**, **Allergies**, **Come back**. Everything is editable. Changing a vital sign re-checks the danger signs straight away.
- The **Evidence** tab shows each fact next to the sentence it came from, and lists anything the AI suggested that was not actually said, so you can check it.
- The **Old prescription** tab (when `ENABLE_VISION=true`) reads a photo of an earlier prescription and shows what is new, stopped or changed.

When everything is right, type your name in the bottom bar and tap **Sign and lock**. The record locks, and the patient screen opens. Nothing is given to the patient before this step; the server enforces it.

### 3. Patient

- If there are urgent danger signs, a red card offers **Create referral ticket**.
- **Make summary** writes a short, plain-language summary (only what the doctor prescribed, never new medicines or doses) and reads it aloud. Tap the big play button to play it for the patient. **Make again** regenerates it, for example after switching language.
- **Give to the patient:**
  - **Phone link (QR)**: the patient scans the code to open a large-print page with the medicines by morning, afternoon and night, plus the audio. Tick **Show diagnosis on the phone page** first if you want the diagnosis included.
  - **Print card**: a printable medicine card.
  - **Reminders**: a calendar file (`.ics`) with medicine reminders.
  - **Export (JSON)**: the record in a FHIR-inspired format, with an audit trail.

Tap **New patient** to start again. Your language choice is kept.

### Header controls

- **Language (globe)**: the language for the summary, alerts and the patient page. **Auto** follows the language heard in the recording (falling back to English if none was detected); pick one by hand to override it.
- **Sun / moon**: switch between dark and light themes (remembered on this device).
- **Menu (three lines)**:
  - **History**: signed records and referral tickets.
  - **Analytics**: documentation time per consultation. Enter how many minutes you normally spend typing a record once, and it shows the measured time saved (demo runs are not counted).
  - **Eval**: the latest evaluation report.

## What it can do

| Area | Features |
|------|----------|
| Capture | Browser microphone, file upload, demo clips, optional live transcription, offline queue that keeps recordings on the device and sends them when the network returns |
| Record | Transcript to structured record (schema validated, one retry, drug-name spelling fix against a formulary), editable form, said-versus-inferred view with transcript quotes |
| Safety | Fixed-rule red flags with the matched inputs, spoken alerts, prescription checks (duplicate drug, same class, allergy), masking of names and phone numbers before the language model |
| Control | Clinician sign-off checked on the server before summary audio, referral, share link, export and reminder file |
| Patient | Plain-language schedule spoken in 9 languages, printable card, share page with QR code, `.ics` reminders |
| Records | Referral tickets and history in SQLite, FHIR-inspired JSON export with an audit trail, analytics of measured time saved |
| Extras | Speaker separation (doctor/patient), prescription photo reading and comparison, evaluation harness |

### Danger signs (red flags)

Red flags come only from these fixed rules, never from the AI. A missing value never triggers a rule.

| Rule | Severity | Triggers when |
|------|----------|---------------|
| `RF_SEPSIS` | urgent | Temperature ≥ 100.4 °F, **and** systolic BP < 100 or pulse > 100, **and** breathlessness or respiratory rate > 22 |
| `RF_HYPOTENSION` | urgent | Systolic BP ≤ 90 |
| `RF_HYPERTENSIVE` | urgent | Systolic ≥ 180 or diastolic ≥ 120 |
| `RF_HYPOXIA` | urgent | SpO2 < 92 |
| `RF_CHEST_PAIN` | urgent | Chest pain mentioned |
| `RF_HIGH_FEVER` | warning | Temperature ≥ 103 °F |
| `RF_HYPERGLYCEMIA` | warning | Blood sugar > 300 |
| `RF_DEHYDRATION` | warning | Vomiting or loose motions, **and** pulse > 100 or systolic BP < 100 |

These are demo-grade rules and have **not** been reviewed by a clinician. See [`docs/SAFETY.md`](docs/SAFETY.md).

### Languages

Summaries, alerts and the patient page: Marathi, Hindi, English, Bengali, Gujarati, Kannada, Punjabi, Tamil and Telugu (the languages with a voice that the Sarvam text-to-speech API accepted). Speech recognition handles code-mixed speech, for example Marathi with English medical words.

## Run it on your computer

### Requirements

- Python 3.11 or newer (developed and tested on 3.14)
- Node.js 18 or newer
- For real speech recognition: **ffmpeg** and **ffprobe** (`sudo apt install ffmpeg`, `brew install ffmpeg`, or `winget install Gyan.FFmpeg`)
- For real mode: a Sarvam AI API key (https://www.sarvam.ai)

### 1. Without an API key (mock mode)

Every step returns canned data with no network, so you can click through the whole app.

```bash
git clone https://github.com/rgb-99/ChikitsaVani.git
cd ChikitsaVani
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

Or start both at once with `./scripts/dev.sh` (Windows: `.\scripts\dev.ps1`). The header shows a **MOCK** badge.

### 2. With the real Sarvam APIs

1. In `.env`, set `SARVAM_API_KEY=` to your key and `MOCK_MODE=false`. Never commit `.env`.
2. Install ffmpeg (see Requirements).
3. Check the key works: `python scripts/smoke_sarvam.py` (from the repo root).
4. Start the app as above.

The microphone only works on `http://localhost` or `https://` addresses (a browser rule).

## Deploy

The live demo runs on Vercel as one project with two services (`vercel.json`): the website, and the backend as a container built from `Dockerfile` (which includes ffmpeg). `/api/*` and `/demo/*` go to the backend, everything else to the website.

```bash
npx vercel login
npx vercel link --yes --project vaidya-saathi     # from the repo root, once
npx vercel deploy --prod
```

Set `SARVAM_API_KEY`, `SIGNING_KEY`, the `TTS_SPEAKER_*` voices, `PUBLIC_BASE_URL` and `CORS_ORIGIN` in the Vercel project first. On Vercel's free plan the server keeps nothing for long: records, share links and history are lost after a few minutes without traffic. The same `Dockerfile` runs on any host with a persistent disk mounted at `/app/data` if you need them to last. Full steps and limits: [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Tests and evaluation

```bash
cd backend && pytest tests/                          # 250+ unit tests, no network needed
RUN_LIVE=1 pytest tests/test_structure_eval.py -s    # live extraction check, needs a key

python eval/build_scenarios.py              # (re)writes eval/scenarios.jsonl (32 synthetic scripts)
python eval/run_eval.py --all               # text mode: language model calls only
python eval/synthesize_audio.py --yes       # builds synthetic audio with Bulbul (prints the call estimate first)
python eval/run_eval.py --all --mode audio --diarize --keyterms-ab
```

Latest committed run (`eval/reports/latest.json`, run `20261103T150541Z`, audio mode, 32 synthetic scenarios):

| Metric | Result |
|--------|--------|
| Overall field F1 | 90.9% |
| Drug name exact match | 93.5% |
| Dose exact match | 58.1% |
| Red-flag precision / recall | 100% / 100% |
| Invented drugs or doses | 0 |
| Speaker-label accuracy | 85.2% |
| Median time: speech recognition / extraction | 13.95 s / 4.36 s |

The run's regression gate **failed** (drug exact match dropped from 96.8% to 93.5% against the previous run). All scenarios are synthetic scripts and synthetic speech, not real clinic audio. Definitions and caveats: [`docs/EVAL.md`](docs/EVAL.md).

## How it works

```
 Browser (React)                         Backend (FastAPI)                         Sarvam AI
 ───────────────                         ─────────────────                         ─────────
 Record ── audio ──────────────────────▶ /api/transcribe ── ffmpeg ──────────────▶ Saaras v4 (speech to text)
                                           (16 kHz WAV, split at silences
                                            into ≤ 28 s pieces)
 Check  ◀── record + red flags ───────── /api/structure ── mask names ───────────▶ sarvam-105b (extraction)
                                           validate, retry once, fix drug spelling
                                           red flags + safety checks (fixed rules)
        ── name ───────────────────────▶ /api/signoff ── HMAC signature, SQLite
 Patient ◀── text + audio ────────────── /api/summary ── check every drug/dose ─▶ sarvam-105b-conversations
                                           template fallback if the check fails    + Bulbul v4 (text to speech)
         ◀── QR, card, .ics, JSON ────── /api/share, /api/card, /api/schedule.ics, /api/export
```

Key rules in the code:

- `backend/sarvam_client.py` is the only file that talks to Sarvam. Every call has a mock version (`MOCK_MODE=true`).
- The language model never decides red flags or doses. Red flags come from `redflags.py`; prescription checks from `safety.py` and `safety_rules.json`.
- The summary may only restate the signed record. Every medicine and dose in it is checked against the record; if the check fails it is regenerated once, then a fixed template is used.
- Sign-off is an HMAC over the record. Any edit after signing breaks the signature, and the server refuses summary audio, referral, share, export and reminders for unsigned records.
- Audio is processed in a temporary folder that is deleted before the response; it is never stored.

**Stack:** FastAPI, Pydantic 2, SQLite, the `sarvamai` SDK, rapidfuzz (drug-name matching), segno (QR codes); React 18, Vite 5, Tailwind CSS 3. Models: `saaras:v4`, `sarvam-105b`, `sarvam-105b-conversations`, `bulbul:v4-flash` (all set by environment variable).

## Project structure

```
backend/
  main.py             API routes
  sarvam_client.py    the only file that imports sarvamai (speech, chat, voice, streaming)
  voice.py            speech to text (ffmpeg, chunking, speaker roles) and text to speech
  llm.py              record extraction and patient summary (prompt, validation, retry, post-check)
  schemas.py          Pydantic models: the data contract
  redflags.py         fixed danger-sign rules and spoken alert text
  safety.py           prescription checks, rules in safety_rules.json
  formulary.py        drug list and spelling correction
  masking.py          hides names, phone numbers and IDs before the language model
  signoff.py          clinician sign-off signature
  share.py            patient share links and QR codes
  card.py, ics.py     printable card, reminder calendar
  export.py           FHIR-inspired JSON export with audit trail
  analytics.py        documentation time and time saved
  vision.py           prescription photo reading
  db.py               SQLite (data/app.db, git-ignored)
  mock_data.py        canned S1 to S3 data for mock mode
  config.py           environment variables
  tests/              unit tests
frontend/
  src/App.jsx         the three-step flow (Record, Check, Patient)
  src/components/     recorder, record form, red-flag banner, summary player, patient share page, ...
  src/api.js          backend calls
demo/                 demo audio (S1 to S3) and reference transcripts
eval/                 evaluation scenarios, harness and committed report
scripts/              dev launchers, Sarvam smoke test, comparison tools
docs/                 spec, decisions, safety, evaluation, demo and deploy guides
Dockerfile            backend container (Python + ffmpeg)
vercel.json           Vercel services and routing
```

## API reference

All routes are under `/api`. Errors return `{"error": "..."}` with an HTTP status. Routes marked 🔒 need a signed record.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Status and whether mock mode is on |
| GET | `/features`, `/languages`, `/demo/scenarios` | Optional features, available languages, demo clips |
| POST | `/transcribe` | Audio file (`audio` form field) to transcript, language and speaker turns |
| POST | `/sync` | Offline queue upload (idempotent by `client_id`) |
| WS | `/stream` | Live transcription (when enabled) |
| POST | `/structure` | Transcript to clinical record with red flags and safety warnings |
| POST | `/redflags`, `/safety` | Re-run the rules on an edited record |
| POST | `/signoff` | Sign and store a record; returns the signed record and its id |
| POST | `/summary` 🔒 | Patient summary text and audio in a language |
| POST | `/alert-audio` | Spoken red-flag alert |
| POST | `/referral` 🔒 | Create a referral ticket |
| POST | `/share` 🔒 | Patient share link and QR code; `GET /share/{token}` reads it |
| GET | `/schedule.ics?record_id=` 🔒 | Medicine reminder calendar |
| POST | `/card` | Printable medicine card (HTML) |
| GET | `/export/{id}.json` 🔒 | FHIR-inspired export |
| GET | `/records`, `/tickets` | History |
| GET, PUT | `/analytics`, `/analytics/baseline` | Time saved; set the typing baseline |
| POST, GET | `/prescription-photo`, `/prescription-photo/{job_id}` | Read an old prescription photo (when enabled) |
| POST | `/reconcile` | Compare a photo's medicines with today's record |
| GET | `/eval/latest` | Latest evaluation report |

## Environment variables

Copy [`.env.example`](.env.example) to `.env`. Model names live in variables so they can change without code edits.

| Variable | Purpose |
|----------|---------|
| `SARVAM_API_KEY` | Your Sarvam AI key (never printed or committed) |
| `MOCK_MODE` | `true` runs with no network and no key |
| `STT_MODEL`, `STT_MODE` | `saaras:v4`; mode `codemix` (chosen on 3 synthetic clips, see `docs/DECISIONS.md`) |
| `LLM_MODEL`, `LLM_MODEL_CONVERSATION` | `sarvam-105b` (extraction), `sarvam-105b-conversations` (summary) |
| `TTS_MODEL`, `TTS_SPEAKER_MR/HI/EN` | `bulbul:v4-flash` and one voice per language |
| `ENABLE_STREAMING` | `true` shows "Live (words as you speak)" under the microphone |
| `ENABLE_DIARIZATION` | `true` separates doctor and patient turns (Batch API, adds about 10 s) |
| `ENABLE_KEYTERMS` | `true` passes the drug list to the speech model (no measured gain, off by default) |
| `ENABLE_VISION` | `true` shows prescription photo reading |
| `ENABLE_PII_MASKING` | `true` (default) masks names, phones and long numbers before the language model |
| `PRODUCTION_MODE` | `true` ignores prescription safety rules that have no reviewer |
| `MAX_AUDIO_SECONDS`, `CORS_ORIGIN`, `PUBLIC_BASE_URL`, `SHARE_TOKEN_TTL_DAYS` | Limits, allowed origin, link base, share-link lifetime |
| `SIGNING_KEY` | Sign-off key shared by all server instances (hosting); empty locally, where `data/signing.key` is used |
| `VITE_API_BASE` (frontend, build time) | Backend origin when it is hosted apart from the frontend; empty otherwise |

## Troubleshooting

| Problem | What to do |
|---------|------------|
| "Microphone permission was denied" | Allow the microphone in the browser address bar, or use **Upload audio** or a demo. |
| "Microphone is not available" | The page must be on `https://` or `http://localhost`. |
| "No speech was detected" | Record again closer to the microphone, or tap into **What was said** and type. |
| "ffmpeg is not installed on the server" | Install ffmpeg and ffprobe and restart the backend. |
| "Cannot reach the server" | Start the backend (`uvicorn main:app --reload --port 8000` in `backend/`). |
| Wrong words in the transcript | Fix them in **What was said**, or go **Back** from Check, edit, and **Extract details** again. |
| Doctor and patient labels swapped | Tap **Swap doctor / patient**. |
| "Audio failed" on the summary | The text is still shown; tap **Retry**. |
| "Clinician sign-off is required" | Sign on the Check screen first; editing after signing needs a new sign-off. |
| Share link or history gone on the live demo | Expected on the free hosting: the server forgets everything after a few idle minutes. |
| Styles look broken after changing `tailwind.config.js` | Restart `npm run dev`. |

## Limitations

- **No real-clinic validation.** Everything was tested on synthetic scripts and synthetic speech.
- **Safety rules are unreviewed.** No clinician has reviewed the red-flag or prescription rules ([`docs/SAFETY.md`](docs/SAFETY.md)). The RF_HYPOTENSION threshold (systolic 90 or below) is flagged for review. The dose-limit table is deliberately empty.
- **Not tested in a real browser by the author:** microphone recording, live transcription, the offline queue and service worker, and the print dialog. The server side of each was tested with recordings and unit tests.
- **Voices were not auditioned.** The text-to-speech voices were accepted by the API but nobody has listened to them all. Malayalam and Odia are not offered because no voice name was accepted.
- **Speech recognition is imperfect.** On synthetic audio the model once heard one drug as another; the doctor's review is the safeguard. Dose extraction is the weakest field (58.1% exact match in the latest run).
- **Handwriting** recognition was only tried on printed text in a handwriting-style font.
- **Masking is best effort.** Names are found by cue words ("my name is", "Mr.", "श्री"), not by a name model. Audio itself is not masked.
- **No accounts or login.** Sign-off records a typed name, not a verified identity. Anyone with the live URL can use it (and spend the deployer's Sarvam credits); anyone with a share link can view it until it expires.
- **Free hosting forgets.** On the live demo, records, share links, history and analytics last only while the server instance is running.
- **FHIR-inspired, not FHIR-compliant.** No ABDM or FHIR compliance is claimed.

## Safety

Red-flag and safety rules in this project are **demo-grade screening rules for decision support**. They must be reviewed by a qualified clinician before any real-world use. This tool is **not a substitute for medical judgement**.

- Red flags and safety warnings come from fixed, human-written rules, never from the language model.
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
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Hosting on Vercel and its limits |
| [`docs/PITCH.md`](docs/PITCH.md) | Pitch text (numbers cite the evaluation report) |
| [`docs/SOURCES.md`](docs/SOURCES.md) | Where every number comes from |

## License

For hackathon use only.
