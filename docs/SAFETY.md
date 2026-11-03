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
| RF_HYPOTENSION   | systolic BP <= 90 (spec table says < 90; see note)     | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HYPERTENSIVE  | systolic ≥ 180 OR diastolic ≥ 120                      | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HYPOXIA       | SpO2 < 92                                              | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_HIGH_FEVER    | temp ≥ 103°F                                           | warning  | —           | —           | Demo-grade, needs clinician  |
| RF_HYPERGLYCEMIA | sugar > 300                                            | warning  | —           | —           | Demo-grade, needs clinician  |
| RF_CHEST_PAIN    | chest pain keyword                                     | urgent   | —           | —           | Demo-grade, needs clinician  |
| RF_DEHYDRATION   | (vomiting OR loose motions) AND (pulse > 100 OR SBP < 100) | warning | —        | —           | Demo-grade, needs clinician  |

> [!NOTE]
> **Open decision for the reviewing clinician:** SPEC section 9 writes RF_HYPOTENSION as systolic < 90, but the SPEC's own demo scenario S2 (BP 90/60) must trigger it. The code uses systolic <= 90 so S2 triggers. A clinician should confirm the threshold (and whether diastolic should count). Temperatures under 45 are read as Celsius and converted. Symptom keywords do not understand negation ("no chest pain" would match).
>
> The spoken alert texts in Marathi and Hindi (`backend/redflags.py` `ALERTS`) are unreviewed drafts and need a native-speaker and clinician check.

> [!CAUTION]
> All red-flag rules are **demo-grade screening rules** and must be reviewed by a qualified clinician before any real-world use.

---

## Prescription Safety Check Rules Review Status

Rules live in `backend/safety_rules.json`. Each has `reviewed_by` and `source`; with `PRODUCTION_MODE=true` rules without a reviewer are ignored. In development they run and are labelled "rule not yet reviewed by a clinician". Output is a warning for the clinician only; the prescription is never edited.

| Rule ID | Type | What it checks | Reviewed By | Review Date | Notes |
| --- | --- | --- | --- | --- | --- |
| SAFE_DUPLICATE_DRUG | duplicate drug | The same medicine listed twice (after formulary spelling normalization) | — | — | Demo-grade |
| SAFE_CLASS_BETA_BLOCKER | same class | Metoprolol + Atenolol | — | — | Demo-grade |
| SAFE_CLASS_ARB | same class | Telmisartan + Losartan | — | — | Demo-grade |
| SAFE_CLASS_STATIN | same class | Atorvastatin + Rosuvastatin | — | — | Demo-grade |
| SAFE_CLASS_PPI | same class | Pantoprazole + Omeprazole | — | — | Demo-grade |
| SAFE_ALLERGY | allergy | A prescribed medicine equals an allergy the clinician typed into the Allergies field | — | — | Allergies are entered by hand, not extracted by the LLM |
| (max daily dose) | dose limit | **Empty.** Never fill from memory; needs a cited reference | — | — | Not active |

---

## Data Handling

- API key stored server-side only; frontend never sees it.
- Audio processed in memory; not persisted to disk.
- Only synthetic/fake patient data used in the repository and demos.
- CORS restricted to configured origin.
- PII masking applied before text reaches the LLM (F28, when implemented).
- Share links: 128-bit random token, expire after `SHARE_TOKEN_TTL_DAYS` (default 7), public page shows first name, schedule, advice, audio and (only if the clinician ticks it) diagnosis; sent with noindex and no-store headers and rate-limited per client (30 per minute, in memory). Anyone holding the link can view it until it expires.

---

## README Statement

The following must appear in the project README:

> Red-flag and safety rules in this project are **demo-grade screening rules for decision support**. They must be reviewed by a qualified clinician before any real-world use. This tool is **not a substitute for medical judgement**.

