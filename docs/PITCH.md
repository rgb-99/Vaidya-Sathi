# Pitch — Slide Text

> Every number here cites the committed evaluation report `eval/reports/latest.json` (run `20261103T150541Z`, 32 synthetic scenarios, audio mode) or an entry in [SOURCES.md](SOURCES.md).
> The evaluation uses synthetic scripts and synthetic speech, not real clinic recordings. Say so on the slide.

---

## Slide 1: Title

**Vaidya Saathi**
Ambient clinical documentation, red-flag triage support, and vernacular patient summaries.

Built with Sarvam AI · Sarvam Campus x IIIT Pune '26

---

## Slide 2: The Problem

**Doctors talk. But they also have to type.**

- Indian OPD consultations happen in code-mixed Marathi, Hindi, and English.
- Notes and prescriptions are typed or handwritten while talking to the patient.
- Patients leave with prescriptions full of shorthand (OD, BD, SOS) they may not understand.
- Frontline health workers may miss danger signs under pressure.

_No statistic is quoted here because none is sourced (see [SOURCES.md](SOURCES.md))._

---

## Slide 3: The Solution

**Vaidya Saathi: the doctor just talks.**

1. **Record** the consultation (or upload audio, or stream it live).
2. **Transcribe** with Sarvam Saaras, code-mixed speech.
3. **Structure**: the record fills in; every fact shows the transcript quote it came from, and anything without a quote is labelled unverified.
4. **Review and sign off**: the doctor edits and signs; nothing downstream works without it.
5. **Speak**: the patient hears the schedule in their language, or scans a QR code for a large-print page.
6. **Alert**: fixed rules flag emergencies and show exactly what triggered them.

---

## Slide 4: Live Demo

_(Run the demo as per [DEMO.md](DEMO.md))_

---

## Slide 5: How It Works

- **Speech-to-text:** Sarvam Saaras v4 (`codemix` mode), with optional speaker separation (clinician and patient) and live streaming.
- **Structuring:** Sarvam 105B returns a strict schema; missing fields stay empty; names and phone numbers are masked before the model sees the text.
- **Red flags:** deterministic, human-written rules, never the language model. The banner shows the matched inputs.
- **Patient summary:** the text may only restate the prescription: every drug and dose is machine-checked, with a fixed template as the fallback. Spoken with Bulbul v4-flash.
- **Human in the loop:** summary audio, referral, share link and export require a clinician sign-off that the server verifies.

---

## Slide 6: Technical Depth (measured, synthetic data)

Source: `eval/reports/latest.json`, run `20261103T150541Z`, **32 synthetic consultations** (Marathi, Hindi, English; includes noisy and fast-speech variants), synthetic speech through the full pipeline.

- Overall field F1: **90.9%** (an earlier run of the same audio: 91.5%).
- Drug name exact match: **93.5%**. Dose exact match: **58.1%**, mostly because the speech model writes "500 milligram" for "500mg".
- Hallucinations (unverified drug, dose, vital, diagnosis or patient detail): **0**.
- Red-flag precision **100%**, recall **100%** (expected flags written by hand from the rule table).
- Speaker-label accuracy: **85.2%**.
- One consultation, measured serially on 3 demo clips: audio to filled record in **3.7 to 11.9 s**; to a spoken summary in **11.1 to 20.5 s** ([EVAL.md](EVAL.md)).
- Known failures, shown on purpose: the speech model once heard "Glimepiride" as "Glycopyrrolate"; the clinician review step is the safeguard.
- 252 automated tests; the evaluation harness has a regression gate (it failed on this run because of speech-model variation, and the report says so).

---

## Slide 7: Safety

- **Decision support, not decision making.**
- Red flags from fixed human-written rules, shown with the matched inputs.
- Patient summary only restates what the clinician prescribed (machine-checked).
- Server-enforced clinician sign-off before summary audio, referral, share link and export.
- Prescription safety warnings (duplicate drug, same class, allergy) are for the clinician only and never edit the prescription.
- Demo uses only fake data; audio is processed in memory.
- **All rules are demo-grade and have not been reviewed by a clinician.** Clinician review is required before any real use.

---

## Slide 8: Reach

- Voices verified with the Sarvam API in **9 languages**: Marathi, Hindi, English, Bengali, Gujarati, Kannada, Punjabi, Tamil, Telugu (not yet auditioned by a listener; Malayalam and Odia are not offered). Source: [SOURCES.md](SOURCES.md).
- Patient share page: no login, large print, audio, expires after 7 days.
- Offline-first capture queues recordings on the device for poor connectivity (server side tested; browser behaviour still to be verified).
- Designed for government OPDs, PHCs, and ASHA workers.
- **Minutes of typing saved:** not yet measured. The Analytics tab measures it from live use; no figure is claimed here.

---

## Slide 9: Built With Sarvam

| Capability               | Sarvam product                    |
| ------------------------ | --------------------------------- |
| Speech-to-text           | Saaras v4 (`codemix` mode)        |
| Speaker separation       | Saaras batch diarization          |
| Live transcription       | Saaras streaming                  |
| Clinical structuring     | sarvam-105b                       |
| Patient summary text     | sarvam-105b-conversations         |
| Voice read-back, alerts  | Bulbul v4-flash                   |
| Prescription photo       | Document Intelligence (extract)   |

---

## Slide 10: What's Next

- Clinician review of the red-flag and prescription safety rules, and of the Marathi and Hindi alert texts.
- Validation on real (consented, de-identified) consultations and real handwriting; today's results are synthetic only.
- A dose normalizer and a "drug not in the formulary" warning, both proposed in [DECISIONS.md](DECISIONS.md) and not yet built.
- Fill the dose-limit table from a cited reference (it is deliberately empty).
- Real deployment hardening: accounts, audit retention, durable rate limiting.

_The export is "FHIR-inspired" and makes no FHIR or ABDM compliance claim._

> Healthcare in India happens in many languages. Vaidya Saathi is a first step, tested so far on Marathi, Hindi and English.
