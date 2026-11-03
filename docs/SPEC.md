# Vaidya Saathi: PRD + TRD

Ambient clinical documentation, red-flag triage support, and vernacular patient summaries. Built for Sarvam Campus x IIIT Pune '26.

---

## Part 0: Instructions for the AI coding agent (read first)

1. This document is the single source of truth. Build exactly what is specified. Do not add auth, payments, databases beyond SQLite, or features not listed.
2. Build order is in TRD section 14. Complete each milestone and make it run before starting the next.
3. Before writing any Sarvam API code, read the current official docs at https://docs.sarvam.ai (speech-to-text, text-to-speech, chat completions). Sarvam setup (from Sarvam's own onboarding): pip install -U sarvamai; create a .env containing SARVAM\_API\_KEY= and add .env to .gitignore; never hardcode or print the key; the first milestone is one chat call with sarvam-105b-conversations; if the key is missing, STOP and ask the human to paste it (no dummy values, no test requests without it). Verified against docs.sarvam.ai when this was updated: chat is client.chat.completions(model=..., messages=\[...\]); speech to text is client.speech\_to\_text.transcribe(file=..., model='saaras:v4', mode='transcribe'); text to speech is client.text\_to\_speech.convert(language\_code=..., text=..., model='bulbul:v4-flash', speaker=...) and returns base64 WAV in audios. The older models saarika and sarvam-m are deprecated: do not use them. Anything not listed here must be read from the docs, never guessed. All model names live in environment variables so they can be changed without code edits.
4. Every external call (STT, LLM, TTS) must have a mock mode (`MOCK_MODE=true`) returning canned data, so the app runs with no network and no API key.
5. Never let an LLM decide red flags or doses. Red flags come only from deterministic rules (TRD section 9).
6. Keep code minimal and readable. Prefer one file per module. Add a short README with run commands.
7. Use only fake patient data. Never store real patient audio.

---

# PART 1: PRODUCT REQUIREMENTS (PRD)

## 1. Overview

**Product name:** Vaidya Saathi (working title)

**One-line pitch:** A doctor or health worker simply talks. The app listens to the code-mixed Marathi/Hindi/English conversation, fills the clinical record automatically, flags urgent red-flag risks using fixed protocol rules, and speaks a simple medicine-schedule summary back to the patient in their own language.

**Event context:** Sarvam Campus x IIIT Pune '26. Theme: build a real-world AI product using Sarvam's multilingual and voice AI. Judged on real-world usefulness, use of Sarvam capabilities, working demo, and presentation. Top 3 projects present.

**Hackathon requirements (from the HackCulture event page):**

- Event: Sarvam Campus x IIIT Pune '26, offline at IIIT Pune, 3 Nov 2026 (listed 10:00 AM to 1:00 PM). The build is solo with no internal time limit; only the showcase slot is fixed, so confirm its length with the organizers.
- Theme: AI Innovation with Sarvam AI. Use multilingual AI, voice AI, document intelligence, or agents to solve a real-world problem; practical and adoptable.
- Build rule: solutions must be built with Sarvam APIs and the tools introduced at the event. Credits for Sarvam APIs and Sarvam Code are provided before the build.
- Participation: the page says individual participation. A solo builder matches this format.
- Showcase: Build Showcase at the end; the top 3 projects present to the campus and receive special prizes.
- Our judging lens: technical depth, creativity, and number of people affected.

## 2. Problem

**Doctor side.** In Indian OPDs and government clinics, doctors see dozens of patients a day. Consultations happen in code-mixed speech, for example: 'BP thoda high aahe, salt intake kami kara, ani he 50mg Metoprolol morning madhe ghet ja'. Doctors manually type notes and prescriptions into records while talking, which eats consultation time. (Do not put a '40% of the day' statistic on slides unless it is sourced.)

**Patient side.** Patients leave with handwritten prescriptions full of shorthand (OD, BD, SOS). Elderly patients and families forget how and when to take medicines, causing poor adherence and repeat visits.

**Frontline side.** ASHA workers and nurses at rural primary health centres describe patient status verbally, and may miss danger signs under pressure. A deterministic checklist can prompt them to escalate.

## 3. Users

| User | Need |
| --- | --- |
| Doctor (primary) | Zero typing during consultation; review and edit auto-filled record |
| Patient / family | Understand medicines in their own language, by audio |
| ASHA worker / nurse (secondary) | Spoken patient status turned into a record plus red-flag alerts |
| Judges / demo audience | See, hear, and understand the value in 3 minutes |

## 4. Goals and non-goals

**Goals**

- G1: Convert a recorded or uploaded code-mixed consultation into a structured clinical record in under 15 seconds.
- G2: Generate a plain-language patient summary with a morning/afternoon/night schedule and speak it in Marathi or Hindi.
- G3: Show deterministic red-flag alerts with the protocol rule that triggered them.
- G4: Give the doctor a review-and-edit step before anything is final.
- G5: A flawless 3-minute live demo with a fallback path.

**Non-goals (do NOT build)**

- No diagnosis generation by AI beyond what the doctor said.
- No AI-recommended drug doses. Doses shown come only from what the clinician said.
- No user accounts, login, billing, or multi-clinic support.
- No real hospital system integration (mock the referral ticket).
- No mobile native app. Responsive web only.

## 5. User stories

- US1: As a doctor, I press record, talk to the patient normally, press stop, and see the record filled in.
- US2: As a doctor, I can edit any field before confirming the record.
- US3: As a doctor, I see the transcript next to the fields so I can check where each value came from.
- US4: As a patient, I tap play and hear my medicine schedule in my language.
- US5: As a nurse, I dictate vitals and symptoms and instantly see a red-flag banner if danger signs match.
- US6: As a nurse, I can create a mock referral ticket with one click after confirming the alert.
- US7: As a presenter, I can run the whole flow from a pre-recorded audio file if the mic fails.

## 6. Features and priorities

### P0 (must ship)

**F1. Audio capture / upload.** Browser mic recording (WebM or WAV) and file upload. Acceptance: record 30-120 s of audio, send to backend, see a progress state.

**F2. Transcription.** Sarvam speech-to-text handling code-mixed Marathi/Hindi/English. Acceptance: transcript displays within 10 s for a 60 s clip; language auto-detected; transcript editable.

**F3. Structured record extraction.** LLM converts transcript into the JSON schema in TRD section 5. Acceptance: output always validates against schema; missing fields are empty strings or empty lists, never invented values.

**F4. Review and edit UI.** All fields editable; a Confirm button locks the record. Acceptance: edits persist to the patient summary generation.

**F5. Patient summary text.** Plain-language summary in the chosen language: what is wrong (as the doctor said), each medicine with when and how, advice, when to return. Acceptance: no medical shorthand, under 120 words, schedule grouped by morning/afternoon/night.

**F6. Patient summary audio.** Sarvam text-to-speech reads the summary. Acceptance: audio plays in the browser, 20-40 seconds, language selector for Marathi / Hindi / English.

### P1 (should ship)

**F7. Red-flag engine.** Deterministic rules over vitals and symptoms (TRD section 9). Acceptance: banner shows severity, matched rule name, and the exact inputs that matched. Text says 'Refer urgently / escalate to doctor'; it never gives doses.

**F8. Spoken red-flag warning.** TTS reads the alert to the nurse in her language.

**F9. Demo mode.** Dropdown of 3 canned scenarios (audio + transcript) that run the full pipeline. Acceptance: works with no mic and no network when MOCK\_MODE is on.

### P2 (stretch)

**F10. Mock referral ticket.** After human confirmation, generate a ticket card (patient, vitals, red flags, timestamp, destination 'District Hospital') and save it to SQLite; show a list.

**F11. Record history.** List of past confirmed records from SQLite.

**F12. Printable prescription card.** Print-friendly view with large text for elderly patients.

### Advanced features (technical depth, creativity, reach)

**F13. Said versus inferred summary (P1).** A two-column clinical summary: the left column holds only facts the clinician or patient actually said, each with a link to the audio timestamp; the right column holds AI-suggested items (for example, a possible red flag) clearly labeled as suggestions. Acceptance: nothing in the left column lacks a quote. Check in the Saaras docs whether timestamps are returned; if not, link to the transcript segment instead.

**F14. Clinician sign-off (P1).** A Sign off button locks the record, stores who signed and when, and is required before the patient summary audio or any referral ticket is created.

**F15. Handwritten prescription photo (P2).** Upload a photo of an old prescription and read it with Sarvam Vision (Document Intelligence: parse or extract). It is an asynchronous job, so read the Document Intelligence docs first. Use fake prescriptions only.

**F16. Patient summary in the patient's language, auto-selected (P1).** Use the detected language to choose the voice, with a manual override.

**F17. Impact view (P2).** A small panel showing minutes of typing saved per consultation in the demo session. Only show measured numbers, not claimed statistics.

**F18. Speaker diarization (P1).** Separate clinician and patient turns automatically (Saaras speaker diarization; read the how-to page for the exact parameter and limits). Extraction uses the roles: orders and prescriptions are accepted only from clinician turns; symptoms and history from patient turns. Acceptance: every utterance shows a speaker label, and a drug mentioned only by the patient is never added to the prescription.

**F19. Drug-name boosting with key terms (P1).** Pass the formulary names to speech to text as key terms (Saaras keyterm prompting; verify the parameter). Acceptance: the evaluation harness (F21) reports drug-name accuracy with and without key terms.

**F20. Real-time streaming (P2).** Stream microphone audio to Saaras real-time streaming, show words as they are spoken, and fill fields progressively with debounced re-extraction every few seconds. Acceptance: first words appear within about 2 s; the final record matches the non-streaming result on the demo scenarios.

**F21. Evaluation harness and results page (P1).** Generate at least 30 synthetic consultations (scripts from clinician-reviewed templates, audio synthesized with Bulbul in different voices and languages, optional added noise), run the full pipeline, and report: per-field extraction F1, drug name and dose exact match, hallucination count (facts without a transcript quote), red-flag precision and recall, and p50 and p95 latency. An /eval page shows the latest run. Acceptance: one command reproduces the numbers, and the pitch quotes only these measured numbers.

**F22. Patient share page via QR (P1).** After sign-off, create a share link and QR code. The patient opens it on their phone and sees a large-print schedule (morning, afternoon, night, with icons), the audio in their language, and a Play again button. No login; the link expires; it contains only the medicine schedule and advice, and diagnosis details only if the clinician ticks them.

**F23. Reminder calendar file (P2).** Export an .ics file from the prescription so the schedule becomes phone reminders.

**F24. Deterministic prescription safety checks (P1).** A small curated rule table (drug classes, duplicate therapy, stated allergies, maximum daily dose entries for the formulary drugs only) shown to the clinician as warnings. Rules are written by humans and reviewed by a clinician; the LLM never decides. Acceptance: a duplicate drug or class, or a drug matching a stated allergy, raises a visible warning, and tests cover each rule.

**F25. Audit trail and export (P1).** Every field stores its source utterance, the model names, and the prompt version. Export a FHIR-inspired JSON bundle (Patient, Encounter, Observation, MedicationRequest). Do not claim ABDM or FHIR compliance; call it FHIR-inspired.

**F26. Prescription photo reconciliation (P2).** Extending F15: after reading an old prescription, show what changed versus today's visit (new, stopped, dose changed).

**F27. Offline-first capture (P2).** A PWA that records audio while offline, queues it in IndexedDB, and syncs when the network returns, with clear status. It targets rural health centers with poor connectivity.

**F28. PII masking before the LLM (P2).** Replace patient names, phone numbers, and ID-like numbers with tokens before text goes to the chat model, and restore them afterwards.

**F29. Language breadth (P1).** Patient summary and read-back in every language Bulbul supports (the docs list 10 Indian languages plus English), language auto-detected with a manual override. Verify the list in the docs.

**F30. Clinician analytics (P2).** Measured minutes saved per consultation (typing-time baseline entered once), counts of red flags and warnings, and language mix. Show only measured numbers.

## 7. Demo scenarios (fake data only)

**S1: OPD hypertension (Marathi-Hindi-English mix).** Doctor: 'Namaskar, kasa ahe? BP check kela, 150/95 ahe, thoda high ahe. Salt kami kara. He Metoprolol 50mg morning madhe ek goli ghet ja, 30 divas. Ani Amlodipine 5mg raatri jevnanantar.' Expected: complaint headache, BP 150/95, two prescription rows, advice low salt.

**S2: Rural PHC emergency (red-flag).** Nurse: 'Patient la 102 fever ahe, breathlessness pan vattoy, BP 90/60 drop zala ahe, pulse 118.' Expected: temp 102, BP 90/60, pulse 118, red-flag banner for possible sepsis with refer-urgently text.

**S3: Diabetes follow-up (Hindi-heavy).** Expected: sugar value, Metformin twice daily after meals, diet advice, return in 2 weeks.

## 8. Success metrics (for the demo and pitch)

- End-to-end latency under 20 s per consultation.
- Field extraction accuracy on the 3 scenarios: at least 90% of expected fields correct (measure with the eval script in TRD section 12).
- Zero invented drugs or doses across test runs.
- Judges understand the value within 30 seconds.

## 9. Safety and ethics requirements

- Clear on-screen label: 'AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.'
- Red flags come from fixed rules written by humans, shown with the matched rule. No LLM-generated risk scores.
- The patient summary may only restate what the clinician prescribed. It must not add new medicines, change doses, or give new advice.
- Human confirmation required before the summary audio is generated and before any referral ticket.
- Only fake data. State this during the demo.
- Frame the product as decision support, not decision making.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| STT mishears drug names | Doctor review step; drug-name fuzzy match against a small local formulary list (TRD 7.4) |
| LLM invents fields | Strict schema, 'leave blank if not stated' prompt, validator, tests |
| Mic or network fails on stage | Demo mode with pre-recorded audio and MOCK\_MODE |
| API model names changed | Names in env vars; verify against docs first |
| Scope creep | P0 first; stretch only after full end-to-end works |

---

# PART 2: TECHNICAL REQUIREMENTS (TRD)

## 1. Architecture

Single web app, two processes:

- **Frontend:** React (Vite) + Tailwind. React + Vite is the chosen stack.
- **Backend:** Python 3.11 + FastAPI + Pydantic v2 + SQLite (via SQLModel or plain sqlite3).

Pipeline per consultation:

1. Browser records audio, POST `/api/transcribe`.
2. Backend calls Sarvam STT, returns transcript.
3. Frontend shows transcript, POST `/api/structure` with the transcript.
4. Backend calls Sarvam chat LLM with the extraction prompt, validates against schema, runs red-flag rules, returns record + red flags.
5. Doctor edits and confirms, then POST `/api/summary` with the confirmed record and language.
6. Backend generates summary text via LLM, then TTS, returns text + audio.
7. Optional: POST `/api/referral` creates a mock ticket.

All Sarvam calls sit behind thin wrapper functions so they can be mocked.

## 2. Tech stack

- Python: fastapi, uvicorn, pydantic, python-multipart, python-dotenv, sarvamai (official SDK, install with pip install -U sarvamai), rapidfuzz, pytest.
- Frontend: React 18, Vite, Tailwind, native MediaRecorder API (no heavy audio libs).
- Storage: SQLite file `data/app.db` (only for P2 history and tickets).
- No Docker needed. One `README` with run commands.

## 3. Repository structure

```
vaidya-saathi/
  CLAUDE.md                # rules for Claude Code (copy of Part 0 plus run/test commands)
  README.md
  .env.example
  .gitignore               # must contain .env
  docs/
    SPEC.md                # this document, exported as Markdown (source of truth)
    SARVAM_NOTES.md        # the Sarvam docs pages the agent needs, pasted or summarized
    DECISIONS.md           # running log: STT mode, voices, model fallbacks, prompt versions
    SAFETY.md              # safety rules, disclaimers, who reviewed the red-flag and safety rules
    EVAL.md                # how to run the evaluation, metric definitions, latest results
    DEMO.md                # demo runbook, scenarios, fallback steps, troubleshooting
    PITCH.md               # slide text; every number must cite its source or an eval run
    SOURCES.md             # citations for any statistic used in the pitch
  backend/
    main.py                # FastAPI app, routes, CORS
    config.py              # loads env vars
    schemas.py             # Pydantic models (section 5 and 18.1)
    sarvam_client.py       # the only file that imports sarvamai
    voice.py               # transcribe(), speak(), diarization, key terms, streaming
    llm.py                 # structure(), summarize()
    redflags.py            # rule engine (section 9)
    safety.py              # prescription safety checks (18.5)
    formulary.py           # drug-name fuzzy match and key-term list (7.4)
    share.py               # share tokens and public schedule data (18.6)
    ics.py                 # reminder calendar file
    export.py              # FHIR-inspired JSON bundle
    masking.py             # PII masking (18.8)
    vision.py              # prescription photo reading with Sarvam Vision
    db.py                  # SQLite helpers
    mock_data.py           # canned transcripts, records, audio paths
    safety_rules.json      # reviewed rule table (18.5)
    tests/
    requirements.txt
  eval/
    scenarios.jsonl        # 30+ synthetic consultations with expected records
    synthesize_audio.py    # builds audio with Bulbul, optional noise
    run_eval.py            # runs the full pipeline and computes metrics
    report.py              # writes the report used by the /eval page
    results/
  frontend/
    src/
      App.jsx
      api.js
      pages/               # Consultation, Share (public), Eval
      components/          # Recorder, DiarizedTranscript, RecordForm, RedFlagBanner,
                           # SafetyWarnings, SummaryPlayer, SignOff, ScheduleCard,
                           # DemoPicker, ReferralCard
    public/                # PWA manifest and service worker
  demo/
    audio/                 # prerecorded fake consultations
    transcripts/
  scripts/
    smoke_sarvam.py        # one chat call: the Sarvam onboarding step
```

## 4. Environment variables

```
SARVAM_API_KEY=
MOCK_MODE=false
STT_MODEL=saaras:v4
STT_MODE=transcribe          # also try codemix on the demo audio; keep what extracts best
LLM_MODEL=sarvam-105b        # reasoning and structuring
LLM_MODEL_CONVERSATION=sarvam-105b-conversations   # dialogue and spoken-style text
TTS_MODEL=bulbul:v4-flash
TTS_SPEAKER_MR=              # pick valid names from the Voices page in the docs
TTS_SPEAKER_HI=
TTS_SPEAKER_EN=
DEFAULT_LANG=mr-IN
MAX_AUDIO_SECONDS=180
CORS_ORIGIN=http://localhost:5173
```

Never hardcode the key. Never commit `.env`.

**Sarvam call reference** (follows Sarvam's published examples; verify any extra parameters in the docs). Keep all of this in one file, `backend/sarvam_client.py`, the only file that imports `sarvamai`.

```python
import os, base64
from sarvamai import SarvamAI

client = SarvamAI(api_subscription_key=os.environ['SARVAM_API_KEY'])

def chat(model, system, user):
    r = client.chat.completions(model=model, messages=[
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user}])
    return r.choices[0].message.content

def stt(path, model='saaras:v4', mode='transcribe'):
    r = client.speech_to_text.transcribe(file=open(path, 'rb'), model=model, mode=mode)
    return r.transcript

def tts(text, language_code, speaker, model='bulbul:v4-flash'):
    r = client.text_to_speech.convert(language_code=language_code, text=text, model=model, speaker=speaker)
    return base64.b64decode(''.join(r.audios))   # WAV bytes
```

Catch `ApiError` (from `sarvamai.core.api_error`) and map 400 bad request, 403 bad key, 422 invalid parameters, 429 rate limit (retry once with backoff). Reasoning models may add text around JSON: always strip code fences and parse the JSON object.

## 5. Data schema (source of truth)

Define in `schemas.py` with Pydantic v2. All fields optional-with-default so partial output validates.

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Patient(BaseModel):
    name: str = ''
    age: str = ''
    sex: str = ''

class Vitals(BaseModel):
    bp: str = ''        # e.g. '150/95'
    temp: str = ''      # degrees F as said, e.g. '102'
    spo2: str = ''
    pulse: str = ''
    resp_rate: str = ''
    sugar: str = ''

class RxItem(BaseModel):
    drug: str = ''
    dose: str = ''        # exactly as clinician said, e.g. '50mg'
    frequency: str = ''   # e.g. 'once daily'
    timing: str = ''      # e.g. 'morning, after food'
    duration: str = ''    # e.g. '30 days'

class RedFlag(BaseModel):
    rule_id: str
    title: str
    severity: Literal['urgent', 'warning']
    matched_inputs: List[str]
    action_text: str

class ClinicalRecord(BaseModel):
    patient: Patient = Patient()
    chief_complaints: List[str] = []
    vitals: Vitals = Vitals()
    diagnosis: str = ''
    prescription: List[RxItem] = []
    advice: List[str] = []
    follow_up: str = ''
    language_detected: str = ''
    red_flags: List[RedFlag] = []

class SummaryResponse(BaseModel):
    text: str
    language: str
    audio_base64: str    # wav
```

## 6. API contract

Base path `/api`. All JSON except the audio upload. Errors return `{ 'error': 'message' }` with a proper status code.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | /health | none | `{status: 'ok', mock: bool}` |
| POST | /transcribe | multipart `audio` file | `{transcript: str, language: str}` |
| POST | /structure | `{transcript: str}` | `ClinicalRecord` (with red\_flags filled) |
| POST | /redflags | `ClinicalRecord` | `{red_flags: RedFlag[]}` (rerun after edits) |
| POST | /summary | `{record: ClinicalRecord, language: 'mr-IN' or 'hi-IN' or 'en-IN'}` | `SummaryResponse` |
| POST | /alert-audio | `{red_flags: RedFlag[], language: str}` | `{text: str, audio_base64: str}` |
| POST | /referral | `{record: ClinicalRecord, confirmed: true}` | `{ticket_id, created_at, destination, payload}` |
| GET | /demo/scenarios | none | list of `{id, title, audio_url, transcript}` |
| GET | /records | none | list of confirmed records (P2) |

`/referral` must return 400 if `confirmed` is not true.

## 7. Module specifications

### 7.1 voice.py

- `transcribe(audio_bytes, filename) -> {transcript, language}`
  - Convert browser WebM to WAV with ffmpeg if the Sarvam endpoint requires it (check docs for accepted formats and max duration; chunk audio if the limit is under 60 s).
  - Use auto language detection if supported; otherwise pass the configured language.
  - If the docs offer a code-mixed or translate-to-English mode, evaluate both on the demo audio and keep whichever extracts better. Record the choice in README.
  - In MOCK\_MODE return the canned transcript matching the uploaded demo filename, or scenario S1 by default.
- `speak(text, language) -> wav_bytes`
  - Respect the TTS per-request character limit from the docs; split on sentence boundaries and concatenate if needed.
  - In MOCK\_MODE return a short bundled wav from `demo/audio/`.

### 7.2 llm.py

- `structure(transcript) -> ClinicalRecord`
  - Call chat completions with the extraction prompt (section 8.1), temperature 0.
  - Strip code fences, parse JSON, validate with Pydantic. On failure retry once with the error message appended. On second failure return an empty record with a visible warning.
  - Post-process drug names with formulary fuzzy match (7.4) but keep the original under a `raw` note only in logs.
- `summarize(record, language) -> str`
  - Call chat completions with the summary prompt (section 8.2), temperature 0.2.
  - Post-check: every drug name in the output must appear in `record.prescription`; every dose must match. If not, regenerate once; if it still fails, fall back to a template-based summary (section 8.3).

### 7.3 redflags.py

Pure Python, no network, no LLM. Input: `ClinicalRecord`. Output: `List[RedFlag]`. Implement the rules in section 9. Include a `parse_bp('90/60') -> (90, 60)` helper and tolerant number parsing (handles '102', '102F', '102 degree'). Symptom matching uses keyword lists in English, Hindi, and Marathi (romanized) against `chief_complaints` plus the raw transcript.

### 7.4 formulary.py

A list of about 40 common drug names (Metoprolol, Amlodipine, Metformin, Paracetamol, Atorvastatin, Telmisartan, Pantoprazole, Azithromycin, Amoxicillin, Cetirizine, ORS, Glimepiride, Losartan, Aspirin, Ondansetron, and similar). `normalize(name) -> str` uses rapidfuzz with a score cutoff of 85, otherwise returns the input unchanged.

### 7.5 db.py (P2)

SQLite with two tables: `records(id, created_at, json)` and `tickets(id, created_at, record_id, payload_json)`. Plain sqlite3 is fine.

## 8. Prompts

### 8.1 Extraction prompt (system)

'You are a clinical documentation assistant for Indian clinics. The input is a transcript of a doctor-patient or nurse-patient conversation, possibly mixing Marathi, Hindi, and English. Extract ONLY information explicitly stated. Never guess, infer, or add drugs, doses, diagnoses, or vitals that were not said. If a field is not mentioned, use an empty string or empty list. Keep drug doses exactly as spoken. Translate complaints and advice into short English phrases. Output ONLY valid JSON matching this shape, with no commentary and no code fences: patient{name,age,sex}, chief\_complaints\[\], vitals{bp,temp,spo2,pulse,resp\_rate,sugar}, diagnosis, prescription\[{drug,dose,frequency,timing,duration}\], advice\[\], follow\_up, language\_detected.'

Include 2 few-shot examples built from scenarios S1 and S2.

### 8.2 Patient summary prompt (system)

'You write medicine instructions for patients in India. Language: {language}. Use very simple spoken words a 65-year-old with little schooling can follow. Use ONLY the diagnosis, medicines, doses, timings, and advice in the provided JSON. Do not add or change any medicine, dose, or advice. Do not use abbreviations like OD or BD. Structure: one sentence on what the doctor found; then Morning, Afternoon, Night, listing which medicine and how many tablets or how much; then simple advice; then when to come back. Maximum 120 words. End with: if you feel worse, go to the hospital immediately.'

### 8.3 Template fallback summary

If the LLM output fails validation, build the summary from templates: 'Take {drug} {dose} {frequency} {timing} for {duration}.' per row, plus advice lines. Translate fixed phrases from a small dictionary for mr, hi, and en.

### 8.4 Alert text template (no LLM)

Fixed strings per rule and language, for example: 'Warning. Signs of possible serious infection. Refer the patient to the hospital urgently and inform the doctor.' Never include doses.

## 9. Red-flag rules (deterministic)

These are demo-grade screening rules for decision support. Mark them in the README as 'to be reviewed by a clinician before any real use'.

| rule\_id | Condition | Severity | Action text |
| --- | --- | --- | --- |
| RF\_SEPSIS | temp >= 100.4F AND (systolic BP < 100 OR pulse > 100) AND (breathlessness keyword OR resp\_rate > 22) | urgent | Possible sepsis. Refer urgently and inform the doctor. |
| RF\_HYPOTENSION | systolic BP < 90 | urgent | Very low blood pressure. Escalate immediately. |
| RF\_HYPERTENSIVE | systolic >= 180 OR diastolic >= 120 | urgent | Severely high blood pressure. Escalate to doctor now. |
| RF\_HYPOXIA | spo2 < 92 | urgent | Low oxygen level. Escalate immediately. |
| RF\_HIGH\_FEVER | temp >= 103F | warning | Very high fever. Inform the doctor. |
| RF\_HYPERGLYCEMIA | sugar > 300 | warning | Very high blood sugar. Inform the doctor. |
| RF\_CHEST\_PAIN | chest pain keyword | urgent | Chest pain reported. Escalate immediately. |
| RF\_DEHYDRATION | (vomiting OR loose motions keyword) AND (pulse > 100 OR systolic BP < 100) | warning | Possible dehydration. Inform the doctor. |

Keyword examples (romanized, extend as needed): breathlessness: 'breathless', 'shortness of breath', 'dam lagna', 'dhap lagte', 'shwas', 'vattoy' near 'breath'; chest pain: 'chest pain', 'chhati dukhna', 'chhatit dukhtay'; vomiting: 'vomiting', 'ulti', 'ulti hote'; loose motions: 'loose motion', 'dast', 'julab'.

Every returned RedFlag lists `matched_inputs`, e.g. \['temp 102F', 'BP 90/60', 'pulse 118', 'breathlessness keyword'\]. Missing inputs never trigger a rule.

## 10. Frontend specification

Single page, three columns on desktop, stacked on mobile.

- **Header:** app name, 'AI-assisted. Clinician must review.' label, mock-mode badge, language selector (Marathi / Hindi / English), DemoPicker dropdown.
- **Left: Recorder + Transcript.** Big record/stop button with timer and waveform-ish pulse, file upload fallback, editable transcript textarea, 'Extract record' button.
- **Center: RecordForm.** Editable fields for patient, complaints (chips), vitals grid, diagnosis, prescription table with add/remove row, advice list, follow-up. 'Confirm record' button (disabled until extraction done).
- **Top of center: RedFlagBanner.** Red for urgent, amber for warning; shows title, matched inputs, action text, and a 'Play alert' button. Recomputes when vitals are edited (calls /redflags).
- **Right: SummaryPlayer.** After confirm: 'Generate patient summary' button, summary text, audio player, 'Download audio'. Shows ReferralCard with 'Create referral ticket' button only when an urgent flag exists and the record is confirmed.
- Loading states for every async step; clear error toasts; works on a phone browser (mic permission handling).
- Style: clean, high contrast, large readable fonts, no heavy animation.

## 11. Error handling and fallbacks

- STT fails or returns empty: show message and allow manual transcript typing.
- LLM returns invalid JSON twice: show empty form with a warning and the transcript, so the doctor can type.
- TTS fails: show the text summary and a 'retry' button.
- Any 429 or timeout: one retry with backoff, then surface the error.
- Global kill switch: `MOCK_MODE=true` makes every endpoint return canned results from `mock_data.py`.
- Log each pipeline step with duration (no patient audio stored on disk beyond the request).

## 12. Testing

- `test_schema.py`: sample LLM outputs (valid, missing fields, extra fields, fenced JSON) all parse or fail gracefully.
- `test_redflags.py`: scenario S2 triggers RF\_SEPSIS and RF\_HYPOTENSION; S1 triggers none; boundary values (SBP 90 vs 89, temp 100.4) behave correctly; empty record triggers nothing.
- `test_structure_eval.py`: run the 3 demo transcripts through `structure()` and compare to expected JSON in `mock_data.py`; print per-field accuracy. Target 90 percent or above.
- Manual: record each scenario three times on a real laptop mic and a phone, with at least one noisy attempt.

## 13. Security and privacy

- API key only on the backend. The frontend never sees it.
- CORS restricted to the configured origin.
- Audio processed in memory; not persisted.
- Only fake data in the repo and the demo.

## 14. Build order (milestones)

1. **M0 (setup):** repo, env, FastAPI health check, Vite app, schemas.py, mock\_data.py with 3 scenarios, MOCK\_MODE end to end returning canned data. App fully clickable with mocks.
2. **M1 (STT):** real `transcribe()`. Test on recorded S1 audio. Compare model options.
3. **M2 (structuring):** real `structure()` with prompt, validation, retry, formulary. Pass the eval at 90 percent.
4. **M3 (summary + TTS):** `summarize()` with post-check and template fallback, `speak()`, audio player in UI.
5. **M4 (red flags):** rules, tests, banner, alert audio.
6. **M5 (polish and demo):** DemoPicker, error states, README, record backup audio, rehearse.
7. **M6 (stretch):** referral ticket, history, printable card.

After each milestone: run tests, commit, and confirm the app still starts.

**Extended milestones (no time limit).** Re-run the tests and the evaluation harness after each one, and keep MOCK\_MODE working throughout.

- **M7:** clinician sign-off (F14), said versus inferred summary (F13), audit trail (F25).
- **M8:** speaker diarization (F18), key-term boosting (F19), language breadth (F29).
- **M9:** evaluation harness (F21). Build this before further prompt tuning and use it to drive improvements.
- **M10:** patient share page with QR (F22), reminder calendar file (F23), prescription safety checks (F24).
- **M11:** prescription photo reading and reconciliation (F15, F26), referral ticket and record history.
- **M12:** real-time streaming (F20), offline-first capture (F27), PII masking (F28), analytics (F30).
- **M13:** polish, demo mode, rehearsal, README, final evaluation run.

## 15. Solo build workflow (Claude Code)

- One builder using Claude Code. Work in plan mode, one milestone per plan, and review each plan before approving it.
- For independent modules (voice, intelligence, frontend, evaluation), run separate sessions on separate git branches or worktrees and merge only when tests pass.
- Quality gate: after every milestone run the unit tests and the evaluation harness (section 18); commit only when green.
- Keep a CLAUDE.md with the Part 0 rules and a DECISIONS.md that logs choices (STT mode, voices, model fallbacks, prompt versions).

Contract: schemas.py and the API table in section 6 stay stable. When they must change, change them first in one session, update the tests, then let other sessions rebase.

## 16. Demo runbook (3 minutes)

1. 0:00 Problem in one sentence: doctors type, patients forget.
2. 0:20 Live consultation S1, two people role-playing. Show transcript, fields filling, edit one field, confirm.
3. 1:10 Play Marathi patient summary. Switch language to Hindi and replay.
4. 1:40 Run S2 (nurse emergency). Red banner appears with matched rules; play spoken alert; create referral ticket after confirming.
5. 2:30 Close: decision support not decision making, rule-based safety, human in the loop, built on Sarvam voice and language models.
6. Fallback: if the mic or network fails, switch to DemoPicker with MOCK\_MODE and continue without comment.

## 17. Definition of done

- A fresh clone runs with `MOCK_MODE=true` and no API key.
- With a valid key, S1, S2, and S3 audio run end to end under 20 seconds each.
- All tests pass; eval at 90 percent or above.
- Red-flag banner correct on S2 and absent on S1.
- Safety label visible; no invented drugs in any output.
- README documents run steps, env vars, model choices, and known limits.

## 18. Advanced features: technical design

This section extends sections 5 to 7 for features F13 to F30. Where a Sarvam parameter is not given here, read the matching docs page (speech-to-text how-to pages for diarization and key terms, real-time streaming, Document Intelligence) before coding.

### 18.1 Schema additions

```python
class Utterance(BaseModel):
    id: str
    speaker: Literal['clinician', 'patient', 'unknown'] = 'unknown'
    text: str = ''
    start_s: float | None = None   # only if the STT response provides timing
    end_s: float | None = None

class Provenance(BaseModel):
    source_utterance_ids: List[str] = []
    model: str = ''
    prompt_version: str = ''

# ClinicalRecord gains:
#   utterances: List[Utterance] = []
#   allergies: List[str] = []
#   said: List[str] = []          # facts with a transcript quote (F13)
#   inferred: List[str] = []      # AI suggestions, always labeled (F13)
#   provenance: dict[str, Provenance] = {}   # keyed by field path (F25)
#   signed_off_by: str = ''
#   signed_at: str = ''           # set only by /signoff, never by the LLM
#   safety_warnings: List[RedFlag] = []      # F24, reuses the RedFlag model
```

### 18.2 New modules

| Module | Purpose |
| --- | --- |
| `voice.py` (extended) | Diarization and key terms in STT; map speaker 0 and 1 to clinician and patient with the heuristic below; streaming variant |
| `safety.py` | Deterministic prescription checks (18.5) |
| `share.py` | Share tokens, expiry, public schedule data |
| `ics.py` | Builds the reminder .ics from the prescription |
| `export.py` | FHIR-inspired JSON bundle |
| `masking.py` | PII tokenization and restore |
| `vision.py` | Sarvam Vision job flow for prescription photos |
| `eval/` | Evaluation harness (18.4) |

**Role heuristic:** the speaker who states drug names, doses, or instructions is the clinician; the other is the patient. Always show a Swap roles button because diarization can mislabel. If only one speaker is detected, mark all turns unknown and fall back to the non-role extraction prompt.

### 18.3 New routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /signoff | `{record, clinician_name}` sets signed\_off\_by and signed\_at, locks the record |
| POST | /share | After sign-off, returns `{token, url, qr_png_base64, expires_at}` |
| GET | /share/{token} | Public, read-only schedule and audio; 404 after expiry; page sends noindex |
| GET | /schedule.ics | Reminder file for a signed record |
| GET | /export/{id}.json | FHIR-inspired bundle |
| POST | /prescription-photo | Upload an image; returns a job id; poll `/prescription-photo/{job}` for the structured result |
| POST | /sync | Accepts queued offline audio uploads and returns their results |
| GET | /eval/latest | The most recent evaluation report |
| WS | /stream | Streaming transcription relay to Sarvam real-time STT |

### 18.4 Evaluation harness (the credibility engine)

Layout: `eval/scenarios.jsonl`, `eval/synthesize_audio.py`, `eval/run_eval.py`, `eval/report.py`, `eval/results/`.

- **Scenarios:** at least 30 synthetic consultations across Marathi, Hindi, English, and mixes, covering normal visits, red-flag cases, noisy audio, fast speech, and multiple drugs. Each line holds the script turns (speaker, text) and the expected record. Hold some scenarios out of the few-shot examples used in prompts, so the evaluation is honest.
- **Audio:** synthesize each turn with Bulbul using different voices for clinician and patient, concatenate, and optionally mix in background noise at a set signal-to-noise ratio. Label results clearly as synthetic, not real clinic audio.
- **Metrics:** per-field extraction F1 (after normalization); drug name and dose exact match; hallucination count (any extracted fact whose evidence is not in the transcript, must be zero); red-flag precision and recall against the expected flags; speaker-label accuracy (F18); drug-name accuracy with and without key terms (F19); p50 and p95 latency per stage.
- **Report:** a JSON file per run plus the /eval page with a table and a comparison against the previous run.
- **Regression gate:** the run fails if hallucinations are above zero or if any headline metric drops by more than 2 points.
- **Rule:** the pitch and slides quote only numbers from the latest report, with the scenario count stated.

### 18.5 Prescription safety checks (F24)

- Data lives in `safety_rules.json` with a `reviewed_by` and `source` field per rule; rules without a reviewer are ignored in production mode.
- Rule types: (1) same drug listed twice; (2) two drugs in the same class (example classes: beta blockers such as metoprolol and atenolol, angiotensin receptor blockers such as telmisartan and losartan, statins, proton pump inhibitors); (3) a drug matching a stated allergy; (4) maximum daily dose entries, which stay empty until filled from a cited reference. Never fill dose limits from memory.
- Output is a warning to the clinician only, with the rule id and the matched items. It never edits the prescription.

### 18.6 Share page and privacy

- Token: 128-bit random, URL-safe. Expiry default 7 days, configurable. Revoke endpoint optional.
- The public page shows first name only, the schedule, advice, and audio; no diagnosis unless ticked; `noindex`; rate-limited.
- QR is generated server-side as a PNG.

### 18.7 Offline-first PWA (F27)

Service worker caches the app shell; recorded audio is saved to IndexedDB with a status; a Sync now button and automatic sync on reconnect call `/sync`; the UI always shows queued, syncing, done, or failed per item. The server must be idempotent: a client-generated id prevents duplicates.

### 18.8 PII masking (F28)

Before text goes to the chat model, replace names, phone numbers, and long digit strings with tokens like `<NAME_1>`; keep the map in memory for the request; restore tokens in the model output. Evidence quotes are validated against the original transcript, not the masked text.

## 19. Additional acceptance criteria

- `eval/run_eval.py` produces a report on 30 or more scenarios with zero hallucinations, and the /eval page renders it.
- Diarization labels are visible and can be swapped; a drug said only by the patient never lands in the prescription.
- The share page works on a phone with no login, shows the schedule and audio, and expires.
- Sign-off is required before share, audio summary, export, or referral.
- Prescription safety checks fire on duplicate drug, same-class, and allergy cases, and each has a test.
- Offline capture queues and syncs without duplicates.
- All advanced features degrade gracefully: if a Sarvam capability is unavailable, the core flow still works and the UI says what is off.
