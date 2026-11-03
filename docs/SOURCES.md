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

**Value:** _TBD — fill from eval run_
**Source:** `eval/results/latest.json`, field `per_field_f1`
**Verified:** No — run evaluation first
**Used in:** Pitch slide 6

### Zero Hallucinated Drugs

**Value:** 0 hallucinated drugs across _N_ test runs
**Source:** `eval/results/latest.json`, field `hallucination_count`
**Verified:** No — run evaluation first
**Used in:** Pitch slide 6

### Red-Flag Precision and Recall

**Value:** _TBD — fill from eval run_
**Source:** `eval/results/latest.json`, fields `redflag_precision`, `redflag_recall`
**Verified:** No — run evaluation first
**Used in:** Pitch slide 6

### End-to-End Latency

**Value:** _TBD — fill from eval run_
**Source:** `eval/results/latest.json`, fields `p50_latency_s`, `p95_latency_s`
**Verified:** No — run evaluation first
**Used in:** Pitch slide 6

### Minutes of Typing Saved

**Value:** _TBD — measure during demo session_
**Source:** Timed comparison during rehearsal
**Verified:** No — measure first
**Used in:** Pitch slide 8

### Supported Languages

**Value:** _TBD — read from Bulbul docs_
**Source:** Sarvam Bulbul documentation, Voices page
**Verified:** No — check docs
**Used in:** Pitch slide 8

---

> [!CAUTION]
> **Never use an unverified number in the pitch.** If a value is TBD, either measure it or remove the claim from the slide.

