# Demo Runbook

> 3-minute live demo. Practice until it is flawless. Fake data only: say so out loud.

## Before the demo

- [ ] Start everything: `./scripts/dev.sh` (Windows: `.\scripts\dev.ps1`), open `http://localhost:5173`.
- [ ] Header shows no **MOCK MODE** badge when you want the real pipeline; shows it in fallback mode.
- [ ] `ffmpeg` and `ffprobe` installed (real mode only). `.env` has `SARVAM_API_KEY` and `MOCK_MODE=false`.
- [ ] Mic works: press **Record**, speak 5 seconds, press **Stop**; the transcript appears.
- [ ] Demo picker tested with S1, S2 and S3 in real mode and again with `MOCK_MODE=true`.
- [ ] Sign-off, summary audio, referral and share link tested once on this machine.
- [ ] Not verified by the author, so test yourself: microphone recording, live transcription, offline queue (turn Wi-Fi off, record, turn it on), printing, voices (listen to all three languages).
- [ ] Language selector tested (Marathi, Hindi, English) and the voices auditioned (`python scripts/test_voice.py <lang> <speaker> "text"`).
- [ ] `demo/audio/S1.wav` to `S3.wav` are synthetic stand-ins (see `demo/README.md`); replace them with fake-patient recordings of the same names if you have them.

## Script

**0:00 Problem (20 s).** "Doctors type while talking; patients leave with shorthand they cannot read."

**0:20 Consultation S1 (50 s).**
1. Press **Record**, role-play S1 (or pick **S1** in the demo picker, which runs the prerecorded clip), press **Stop**. The transcript appears in the editable panel.
2. Press **Extract record**. Show complaints, BP 150/95, two prescription rows, advice.
3. Edit one field. Point at the **Said / AI-suggested** panel (each said fact shows its transcript quote). Type the clinician name and press **Sign off and lock record** (the form locks; summary, referral and export need this).

**1:10 Patient summary (30 s).** Press **Generate patient summary**, play the audio. Switch the language to Hindi, press **Generate** again. Point out simple words and the morning, afternoon, night schedule.

**1:40 Emergency S2 (50 s).** Pick **S2**, press **Extract record**. A red banner shows RF_SEPSIS and RF_HYPOTENSION with the matched inputs. Press **Play alert**. Type a clinician name, press **Sign off and lock record**, then **Create referral ticket**. **Export** downloads the FHIR-inspired JSON.

**2:30 Close (30 s).** "Decision support, not decision making. Red flags are fixed rules, the doctor always reviews, built on Sarvam voice and language models."

Optional extras, in the order they appear after sign-off (only demo what you have rehearsed):
- **Create patient share link** shows a QR code and link; open it on a phone (same network and `PUBLIC_BASE_URL` set to the laptop's address) to show the large-print schedule with the audio.
- **Download reminder calendar (.ics)**, **Print medicine card**, **Export (FHIR-inspired JSON)**.
- Tabs: **History** (signed records and tickets), **Analytics** (enter your typing baseline once; shows measured time only, demo runs excluded), **Eval** (latest evaluation report).
- With `ENABLE_VISION=true`: **Upload photo** of a sample prescription (`demo/prescriptions/rx1.png`) to see what changed against today's record.
- With `ENABLE_STREAMING=true`: **Record live** shows words as you speak.
- With `ENABLE_DIARIZATION=true`: coloured clinician and patient turns with **Swap roles** (adds about 10 s).

## Fallbacks

| Problem | Action |
| --- | --- |
| Mic blocked or broken | Use the demo picker (prerecorded clip) or "or upload an audio file". |
| Network or Sarvam down | Stop the backend, set `MOCK_MODE=true`, restart with `./scripts/dev.sh`. Every step returns canned data (the audio is a placeholder tone). |
| STT garbage | Edit the transcript and press **Extract record** again. |
| LLM fails twice | An empty form with a warning appears; fill it by hand. |
| TTS fails | The summary text still shows with a **Retry** button. |

## Troubleshooting

- **CORS error:** `CORS_ORIGIN` in `.env` must match the frontend URL.
- **Key error (502, "rejected the API key"):** check `SARVAM_API_KEY` in `.env`.
- **400 not valid audio / 413 too long (limit 180 s):** use another file.
- **Mic blocked:** allow it in the address bar (needs localhost or https).
- **"Cannot reach the server":** the backend is not running on port 8000.
