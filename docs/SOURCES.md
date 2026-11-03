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

**Value:** overall field F1 95.6% over 32 synthetic scenarios, text mode (no STT), run 20261103T141228Z
**Source:** `eval/reports/latest.json`, `metrics.overall_f1` and `metrics.per_field`
**Verified:** Yes for text mode only; audio-mode numbers pending
**Used in:** Pitch slide 6

### Zero Hallucinated Drugs

**Value:** 0 hallucinations (unverified drug, dose, vital, diagnosis or patient detail) across 32 synthetic scenarios, text mode, run 20261103T141228Z
**Source:** `eval/reports/latest.json`, `metrics.hallucinations`
**Verified:** Yes for text mode only
**Used in:** Pitch slide 6

### Red-Flag Precision and Recall

**Value:** precision 100.0%, recall 100.0% on 32 synthetic scenarios (expected flags hand-written from the rule table), run 20261103T141228Z
**Source:** `eval/reports/latest.json`, `metrics.redflag_precision`, `metrics.redflag_recall`
**Verified:** Yes for text mode; the rules are demo-grade and clinician review is pending
**Used in:** Pitch slide 6

### End-to-End Latency

**Value:** not yet measured end to end. Text mode measured only extraction (p50 4.21 s, p95 7.59 s); STT, summary and speech stages are not in the report yet
**Source:** `eval/reports/latest.json`, `metrics.latency_s`
**Verified:** No — run audio mode
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

