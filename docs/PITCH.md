# Pitch — Slide Text

> Every number in this pitch must cite its source or an evaluation run.
> Do not put unverified statistics on slides.

---

## Slide 1: Title

**Vaidya Saathi**
Ambient clinical documentation, red-flag triage, and vernacular patient summaries.

Built with Sarvam AI · Sarvam Campus x IIIT Pune '26

---

## Slide 2: The Problem

**Doctors talk. But they also have to type.**

- Indian OPD consultations happen in code-mixed Marathi, Hindi, and English.
- Doctors manually type notes and prescriptions while talking to patients.
- Patients leave with handwritten prescriptions full of shorthand (OD, BD, SOS) they don't understand.
- Frontline health workers may miss danger signs under pressure.

> [!IMPORTANT]
> Do not claim "40% of the day spent typing" or any other statistic unless it is sourced. See [SOURCES.md](SOURCES.md).

---

## Slide 3: The Solution

**Vaidya Saathi: the doctor just talks.**

1. **Record** — the consultation is captured as audio.
2. **Transcribe** — Sarvam Saaras handles code-mixed speech.
3. **Structure** — the clinical record fills automatically.
4. **Review** — the doctor edits and confirms.
5. **Speak** — the patient hears their medicine schedule in their own language.
6. **Alert** — deterministic rules flag emergencies instantly.

---

## Slide 4: Live Demo

_(Run the demo as per [DEMO.md](DEMO.md))_

---

## Slide 5: How It Works

- **Speech-to-Text:** Sarvam Saaras v4, code-mixed Marathi/Hindi/English.
- **Structuring:** Sarvam LLM extracts fields into a strict schema. No hallucination — missing fields stay empty.
- **Red Flags:** Deterministic rules (not AI). Shows the exact inputs that triggered the alert.
- **Patient Summary:** Plain-language schedule in the patient's language via Sarvam Bulbul TTS.
- **Human in the loop:** Clinician reviews and confirms before anything is final.

---

## Slide 6: Technical Depth

- Extraction accuracy: _[cite eval run]_ on _[N]_ synthetic consultations.
- Zero hallucinated drugs across _[N]_ test runs — _[cite eval run]_.
- Red-flag precision: _[cite eval run]_. Recall: _[cite eval run]_.
- p50 latency: _[cite eval run]_. p95: _[cite eval run]_.
- Drug-name fuzzy matching against a local formulary.
- Deterministic prescription safety checks (duplicate drugs, same-class, allergy).

> [!IMPORTANT]
> Fill in all bracketed numbers from the latest `eval/results/latest.json` before presenting.

---

## Slide 7: Safety

- **Decision support, not decision making.**
- Red flags from fixed human-written rules, shown with the matched rule.
- Patient summary only restates what the clinician prescribed.
- Human confirmation required before summary audio or referral.
- Demo uses only fake data.
- All rules are demo-grade — clinician review required before real use.

---

## Slide 8: Impact

- Minutes of typing saved per consultation: _[cite measured number from demo session]_.
- Works in every language Bulbul supports: _[list from docs]_.
- Designed for government OPDs, PHCs, and ASHA workers.

> Only show measured numbers, not claimed statistics.

---

## Slide 9: Built With Sarvam

| Capability              | Sarvam Product        |
| ----------------------- | --------------------- |
| Speech-to-Text          | Saaras v4             |
| Code-mixed transcription| Saaras v4             |
| Clinical structuring    | sarvam-105b           |
| Patient summary text    | sarvam-105b-conversations |
| Voice read-back         | Bulbul v4-flash       |
| Speaker diarization     | Saaras diarization    |
| Prescription photo      | Document Intelligence |

---

## Slide 10: What's Next

- Clinician-reviewed safety rules for real deployment.
- ABDM / FHIR-inspired export for health record systems.
- Offline-first PWA for rural health centres with poor connectivity.
- More languages, more voices, real-time streaming.

> "Healthcare in India happens in every language. Vaidya Saathi listens in all of them."

