# Safety Rules, Disclaimers, and Review Status

> This document tracks all safety-related rules, disclaimers, and their review status.
> No rule should be active in production mode without a recorded reviewer.

---

## On-Screen Disclaimer

Displayed permanently in the app header:

> **AI-assisted documentation. Clinician must review. Not a substitute for medical judgement.**

---

## Core Safety Principles

1. **Decision support, not decision making.** The app assists documentation; it does not diagnose or prescribe.
2. **Red flags are deterministic.** All red-flag alerts come from fixed, human-written rules — never from the LLM.
3. **No invented data.** The LLM extracts only what was explicitly stated. Missing fields stay empty.
4. **Patient summary restates only.** The summary may only repeat what the clinician prescribed. It must not add medicines, change doses, or give new advice.
5. **Human confirmation required.** Summary audio and referral tickets are generated only after the clinician confirms the record.
6. **Fake data only.** All demo data is synthetic. No real patient information is stored.

---

## Red-Flag Rules Review Status

| Rule ID          | Condition Summary                                      | Severity | Reviewed By | Review Date | Notes                        |
| ---------------- | ------------------------------------------------------ | -------- | ----------- | ----------- | ---------------------------- |
| RF_SEPSIS        | temp ≥ 100.4 AND (SBP < 100 OR pulse > 100) AND (breathlessness OR resp_rate > 22) | urgent | — | — | Demo-grade, needs clinician |
| RF_HYPOTENSION   | systolic BP < 90                                       | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HYPERTENSIVE  | systolic ≥ 180 OR diastolic ≥ 120                      | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HYPOXIA       | SpO2 < 92                                              | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HIGH_FEVER    | temp ≥ 103°F                                           | warning  | —           | —           | Demo-grade, needs clinician  |
| RF_HYPERGLYCEMIA | sugar > 300                                            | warning  | —           | —           | Demo-grade, needs clinician  |
| RF_CHEST_PAIN    | chest pain keyword                                     | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_DEHYDRATION   | (vomiting OR loose motions) AND (pulse > 100 OR SBP < 100) | warning | —        | —           | Demo-grade, needs clinician  |

> [!CAUTION]
> All red-flag rules are **demo-grade screening rules** and must be reviewed by a qualified clinician before any real-world use.

---

## Prescription Safety Check Rules Review Status

| Rule Type              | Example                                        | Reviewed By | Review Date | Notes                       |
| ---------------------- | ---------------------------------------------- | ----------- | ----------- | --------------------------- |
| Duplicate drug         | Same drug listed twice                         | —           | —           | Demo-grade                  |
| Same-class duplicate   | Two beta-blockers (e.g. Metoprolol + Atenolol) | —           | —           | Demo-grade                  |
| Allergy match          | Drug matches a stated allergy                  | —           | —           | Demo-grade                  |
| Max daily dose         | (empty — needs cited reference to fill)        | —           | —           | Never fill from memory      |

---

## Data Handling

- API key stored server-side only; frontend never sees it.
- Audio processed in memory; not persisted to disk.
- Only synthetic/fake patient data used in the repository and demos.
- CORS restricted to configured origin.
- PII masking applied before text reaches the LLM (F28, when implemented).

---

## README Statement

The following must appear in the project README:

> Red-flag and safety rules in this project are **demo-grade screening rules for decision support**. They must be reviewed by a qualified clinician before any real-world use. This tool is **not a substitute for medical judgement**.

