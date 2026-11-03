# Demo Runbook

> Step-by-step guide for the 3-minute live demo.
> Practice this until it's flawless.

---

## Before the Demo

- [ ] Laptop charged, plugged in.
- [ ] Browser open with the app loaded (`http://localhost:5173`).
- [ ] Backend running (`uvicorn backend.main:app`).
- [ ] Mic tested — record a short clip and verify transcript appears.
- [ ] Backup: `MOCK_MODE=true` ready to toggle if network/mic fails.
- [ ] Pre-recorded demo audio files in `demo/audio/` ready (`S1.wav`-`S3.wav` are synthetic stand-ins, see `demo/README.md`; replace with fake-patient recordings).
- [ ] `ffmpeg` and `ffprobe` installed on the demo machine (real mode only).
- [ ] DemoPicker dropdown tested with all 3 scenarios.
- [ ] Language selector tested (Marathi, Hindi, English).

---

## Demo Script (3 minutes)

### 0:00 — Problem Statement (20 seconds)

> "In Indian clinics, doctors see dozens of patients a day. They talk in mixed Marathi, Hindi, and English — but they have to type everything into records while talking. Patients leave with prescriptions full of shorthand they can't read. Vaidya Saathi fixes both."

### 0:20 — Live Consultation S1: OPD Hypertension (50 seconds)

1. Two people role-play the doctor-patient conversation (S1 script).
2. Press **Record** — show the timer and waveform animation.
3. Speak the S1 dialogue (Marathi-Hindi-English mix).
4. Press **Stop** — transcript appears.
5. Click **Extract Record** — fields fill automatically.
6. Point out: complaints, vitals (BP 150/95), two prescription rows, advice.
7. Edit one field (e.g., fix a spelling) to show the review step.
8. Click **Confirm Record**.

### 1:10 — Patient Summary (30 seconds)

1. Click **Generate Patient Summary**.
2. Summary text appears in Marathi — read it aloud or play the audio.
3. Switch language to Hindi — replay. Point out: simple words, no abbreviations, morning/afternoon/night schedule.
4. "The patient hears their medicine schedule in their own language."

### 1:40 — Emergency S2: Red-Flag Triage (50 seconds)

1. Switch to DemoPicker → S2 (Rural PHC Emergency), or role-play the nurse dictation.
2. Run the pipeline — transcript appears, record fills.
3. **Red banner appears** — "Possible Sepsis: Refer urgently."
4. Point out the matched inputs: temp 102°F, BP 90/60, pulse 118, breathlessness.
5. Click **Play Alert** — the spoken warning plays in the nurse's language.
6. Click **Create Referral Ticket** (after confirming) — ticket card appears.
7. "Deterministic rules, not AI guesses. The nurse gets a clear action."

### 2:30 — Closing (30 seconds)

> "Vaidya Saathi is decision support, not decision making. Red flags come from fixed medical rules, not AI. The doctor always reviews. Built on Sarvam's multilingual voice and language models — because healthcare in India happens in every language."

---

## Fallback Plan

| Problem              | Action                                                             |
| -------------------- | ------------------------------------------------------------------ |
| Mic doesn't work     | Use DemoPicker with pre-recorded audio. Continue without comment.  |
| Network is down      | Set `MOCK_MODE=true`, restart backend. All endpoints return canned data. |
| STT returns garbage  | Show the editable transcript, type corrections, continue the flow. |
| LLM fails            | Empty form appears with warning — fill manually to show the concept. |
| TTS fails            | Show the text summary, skip audio playback.                       |
| App crashes          | Have a second terminal ready. Restart and use DemoPicker.          |

---

## Scenarios Reference

| ID | Title                                    | Language Mix            | Key Points                             |
| -- | ---------------------------------------- | ----------------------- | -------------------------------------- |
| S1 | OPD Hypertension                         | Marathi-Hindi-English   | BP 150/95, Metoprolol, Amlodipine      |
| S2 | Rural PHC Emergency                      | Marathi-Hindi           | Temp 102, BP 90/60, pulse 118, sepsis  |
| S3 | Diabetes Follow-up                       | Hindi-heavy             | Sugar 180, Metformin, diet advice      |

---

## Troubleshooting

- **CORS error:** Check that `CORS_ORIGIN` in `.env` matches the frontend URL.
- **API key error:** Verify `SARVAM_API_KEY` is set in `.env` and not expired.
- **Audio format error (400):** the file is not valid audio. Browser WebM and WAV/MP3/M4A/OGG/FLAC are accepted; the backend decodes with ffmpeg when needed.
- **Audio too long (413):** the limit is 180 s (`MAX_AUDIO_SECONDS`). Longer clips are split into 28 s pieces for Sarvam automatically.
- **Microphone blocked:** allow it in the address bar (needs localhost or https) or use "upload an audio file".
- **Slow response:** Check network; consider using `MOCK_MODE` for the demo.

