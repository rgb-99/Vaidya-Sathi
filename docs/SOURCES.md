# Sources and Citations

> Every statistic used in the pitch, slides, or README must be listed here with its source.
> Do not use any number that does not have an entry in this file.

---

## Format

```
### [Claim]
**Value:** ...
**Source:** ...
**Verified:** Yes / No
**Used in:** Pitch slide N / README / Demo script
```

---

### Extraction Accuracy

**Value:** overall field F1 91.5% over 32 synthetic scenarios, audio mode (synthetic speech through STT and diarization), run 20261103T144437Z; text mode 98.8% (scripts only)
**Source:** `eval/reports/latest.json`, `metrics.overall_f1` and `metrics.per_field`
**Verified:** Yes (synthetic audio only; not real clinic recordings)
**Used in:** Pitch slide 6

### Zero Hallucinated Drugs

**Value:** 0 hallucinations (unverified drug, dose, vital, diagnosis or patient detail) across 32 synthetic scenarios, audio mode, run 20261103T144437Z. Note: an STT mishearing (Glimepiride heard as Glycopyrrolate in E06) is not counted as a hallucination because the word is in the transcript
**Source:** `eval/reports/latest.json`, `metrics.hallucinations`
**Verified:** Yes
**Used in:** Pitch slide 6

### Red-Flag Precision and Recall

**Value:** precision 100.0%, recall 100.0% on 32 synthetic scenarios, audio mode (expected flags hand-written from the rule table), run 20261103T144437Z
**Source:** `eval/reports/latest.json`, `metrics.redflag_precision`, `metrics.redflag_recall`
**Verified:** Yes; the rules themselves are demo-grade and clinician review is pending
**Used in:** Pitch slide 6

### End-to-End Latency

**Value:** audio mode, run 20261103T144437Z: STT p50 10.78 s / p95 28.54 s (diarized batch job, 4 jobs in parallel); structure() p50 3.29 s / p95 6.61 s. Summary and speech stages are not in the report; end-to-end p95 is above the 20 s target
**Source:** `eval/reports/latest.json`, `metrics.latency_s`
**Verified:** Yes for the stages listed
**Used in:** Pitch slide 6

### Minutes of Typing Saved

**Value:** _TBD — measure during demo session_
**Source:** Timed comparison during rehearsal
**Verified:** No — measure first
**Used in:** Pitch slide 8

### Supported Languages

**Value:** the app offers 9 languages (Marathi, Hindi, English, Bengali, Gujarati, Kannada, Punjabi, Tamil, Telugu). Bulbul also lists Malayalam and Odia, but no voice name was accepted by the API, so they are not offered
**Source:** `sarvamai` SDK type for `text_to_speech.convert` and live API checks on 2026-11-03 (`docs/SARVAM_NOTES.md`)
**Verified:** Voices accepted by the API, not auditioned by a listener
**Used in:** Pitch slide 8

---

> [!CAUTION]
> **Never use an unverified number in the pitch.** If a value is TBD, either measure it or remove the claim from the slide.

