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
1. On the **Record** screen, tap the big microphone, role-play S1 (or tap **S1** under "Try a demo", which runs the prerecorded clip), tap it again to stop. The transcript appears in the editable "What was said" box.
2. Press **Extract details** (bottom right). The **Check** screen opens: show complaints, BP 150/95, two medicines, advice.
3. Edit one field. Open the **Evidence** tab (each said fact shows its transcript quote; AI-suggested facts are listed separately). Type the doctor name in the bottom bar and press **Sign and lock** (the form locks and the **Patient** screen opens; summary, referral and export need this).

**1:10 Patient summary (30 s).** Press **Make summary**, tap the big play button. Switch the language to Hindi (globe menu in the header), press **Make again**. Point out simple words and the morning, afternoon, night schedule.

**1:40 Emergency S2 (50 s).** Press **New patient**, tap **S2**, press **Extract details**. A red "Danger signs found" banner shows RF_SEPSIS and RF_HYPOTENSION with the matched inputs. Press **Play alert**. Type a doctor name, press **Sign and lock**, then **Create referral ticket** on the Patient screen. **Export (JSON)** downloads the FHIR-inspired JSON.

**2:30 Close (30 s).** "Decision support, not decision making. Red flags are fixed rules, the doctor always reviews, built on Sarvam voice and language models."

Optional extras, on the Patient screen under "Give to the patient" (only demo what you have rehearsed):
- **Phone link (QR)** shows a QR code and link; open it on a phone (same network and `PUBLIC_BASE_URL` set to the laptop's address) to show the large-print schedule with the audio.
- **Reminders** (.ics calendar file), **Print card**, **Export (JSON)** (FHIR-inspired).
- Header menu (☰): **History** (signed records and tickets), **Analytics** (enter your typing baseline once; shows measured time only, demo runs excluded), **Eval** (latest evaluation report).
- With `ENABLE_VISION=true`: on the Check screen, the **Old prescription** tab, **Upload photo** of a sample prescription (`demo/prescriptions/rx1.png`) to see what changed against today's record.
- With `ENABLE_STREAMING=true`: **Live (words as you speak)** under the microphone; extraction starts by itself when you stop.
- With `ENABLE_DIARIZATION=true`: doctor and patient turns as chat bubbles with **Swap doctor / patient** (adds about 10 s).

## Fallbacks

| Problem | Action |
| --- | --- |
| Mic blocked or broken | Tap a demo under "Try a demo" (prerecorded clip), **Upload audio**, or **Type it instead**. |
| Network or Sarvam down | Stop the backend, set `MOCK_MODE=true`, restart with `./scripts/dev.sh`. Every step returns canned data (the audio is a placeholder tone). |
| STT garbage | Go **Back** to Record, edit the transcript and press **Extract details** again. |
| LLM fails twice | An empty form with a warning appears; fill it by hand. |
| TTS fails | The summary text still shows with a **Retry** button. |

## Troubleshooting

- **CORS error:** `CORS_ORIGIN` in `.env` must match the frontend URL.
- **Key error (502, "rejected the API key"):** check `SARVAM_API_KEY` in `.env`.
- **400 not valid audio / 413 too long (limit 180 s):** use another file.
- **Mic blocked:** allow it in the address bar (needs localhost or https).
- **"Cannot reach the server":** the backend is not running on port 8000.
