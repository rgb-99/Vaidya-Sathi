# Demo Runbook

> 3-minute live demo. Practice until it is flawless. Fake data only: say so out loud.

## Before the demo

- [ ] Start everything: `./scripts/dev.sh` (Windows: `.\scripts\dev.ps1`), open `http://localhost:5173`.
- [ ] Header shows no **MOCK MODE** badge when you want the real pipeline; shows it in fallback mode.
- [ ] `ffmpeg` and `ffprobe` installed (real mode only). `.env` has `SARVAM_API_KEY` and `MOCK_MODE=false`.
- [ ] Mic works: press **Record**, speak 5 seconds, press **Stop**; the transcript appears.
- [ ] Demo picker tested with S1, S2 and S3 in real mode and again with `MOCK_MODE=true`.
- [ ] Language selector tested (Marathi, Hindi, English) and the voices auditioned (`python scripts/test_voice.py <lang> <speaker> "text"`).
- [ ] `demo/audio/S1.wav` to `S3.wav` are synthetic stand-ins (see `demo/README.md`); replace them with fake-patient recordings of the same names if you have them.

## Script

**0:00 Problem (20 s).** "Doctors type while talking; patients leave with shorthand they cannot read."

**0:20 Consultation S1 (50 s).**
1. Press **Record**, role-play S1 (or pick **S1** in the demo picker, which runs the prerecorded clip), press **Stop**. The transcript appears in the editable panel.
2. Press **Extract record**. Show complaints, BP 150/95, two prescription rows, advice.
3. Edit one field, press **Confirm record** (the form locks).

**1:10 Patient summary (30 s).** Press **Generate patient summary**, play the audio. Switch the language to Hindi, press **Generate** again. Point out simple words and the morning, afternoon, night schedule.

**1:40 Emergency S2 (50 s).** Pick **S2**, press **Extract record**. A red banner shows RF_SEPSIS and RF_HYPOTENSION with the matched inputs. Press **Play alert**. Press **Confirm record**, then **Create referral ticket**.

**2:30 Close (30 s).** "Decision support, not decision making. Red flags are fixed rules, the doctor always reviews, built on Sarvam voice and language models."

Not built yet (do not demo): clinician sign-off, share page, history, prescription photos.

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
