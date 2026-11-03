# Evaluation Guide

> How to run the evaluation harness, metric definitions, and latest results.

---

## Overview

The evaluation harness tests the full pipeline (STT → structuring → red flags → summary) against synthetic consultations and produces a reproducible metrics report.

## Directory Layout

```
eval/
  scenarios.jsonl        # 30+ synthetic consultations with expected records
  synthesize_audio.py    # builds audio with Bulbul, optional noise
  run_eval.py            # runs the full pipeline and computes metrics
  report.py              # writes the report used by the /eval page
  results/               # timestamped JSON reports
```

## Running the Evaluation

```bash
python eval/build_scenarios.py                 # (re)writes eval/scenarios.jsonl, 32 synthetic scripts; review it before spending audio credits
python eval/run_eval.py --all                  # text mode: scripts go straight to extraction + red flags (LLM calls only)

python eval/synthesize_audio.py                # prints the Bulbul call estimate and stops
python eval/synthesize_audio.py --yes          # synthesizes eval/audio/*.wav (synthetic speech, noise on N*, fast on F*)
python eval/run_eval.py --all --mode audio     # adds STT; optional --diarize, --keyterms, --keyterms-ab
```

`run_eval.py` exits 1 if the regression gate fails. Reports: `eval/results/<run>.json` (git-ignored) and `eval/reports/latest.json` (committed; also holds the previous run's metrics). The `/eval` page and `GET /api/eval/latest` show the latest report.

---

## Metrics

| Metric                        | Definition                                                                                   | Target       |
| ----------------------------- | -------------------------------------------------------------------------------------------- | ------------ |
| Per-field extraction F1       | F1 score per schema field after normalization                                                | ≥ 90%        |
| Drug name exact match         | Extracted drug name matches expected (case-insensitive, after formulary normalization)        | ≥ 90%        |
| Drug dose exact match         | Extracted dose matches expected (exact string)                                               | ≥ 90%        |
| Hallucination count           | Facts in the output without a corresponding transcript quote. **Must be zero.**              | 0            |
| Red-flag precision            | Correct flags / total flags raised                                                           | ≥ 95%        |
| Red-flag recall               | Correct flags / total flags expected                                                         | 100%         |
| Speaker-label accuracy (F18)  | Correct speaker labels / total utterances                                                    | ≥ 85%        |
| Drug accuracy with key terms  | Drug name match with key-term boosting vs without (F19)                                      | Improvement  |
| p50 latency                   | Median end-to-end time per consultation                                                      | < 15s        |
| p95 latency                   | 95th percentile end-to-end time                                                              | < 20s        |

---

## Scenarios

- At least 30 synthetic consultations.
- Languages: Marathi, Hindi, English, and code-mixed.
- Cases: normal visits, red-flag emergencies, noisy audio, fast speech, multiple drugs.
- Some scenarios are held out from the few-shot examples in prompts (honest evaluation).
- All audio is synthetic (Bulbul TTS) — clearly labeled, never real clinic recordings.

---

## Regression Gate

A run **fails** if:

- Hallucination count > 0
- Any headline metric drops by more than 2 points from the previous run

---

## Latest Results

Committed report: `eval/reports/latest.json`, run `20261103T150541Z`, **audio mode** (Bulbul speech -> Saaras `codemix` with diarization -> extraction -> red flags), **32 synthetic scenarios**. All audio is synthetic speech (clean TTS, noise and fast variants included), not real clinic audio. The code was final (prompt v3, PII masking on) for this run.

| Metric | This run | Previous audio run `20261103T144437Z` | Text mode (`20261103T143616Z` and `20261103T145613Z`; scripts straight to extraction, JSON not committed) |
| --- | --- | --- | --- |
| Overall field F1 | 90.9 % | 91.5 % | 98.8 %, 99.4 % |
| Drug name exact match | 93.5 % | 96.8 % | 100 % |
| Dose exact match | 58.1 % | 58.1 % | 100 % |
| Red-flag precision / recall | 100.0 % / 100.0 % | 100 % / 100 % | 100 % / 100 % and 100 % / 92.9 % |
| Hallucinations | 0 | 0 | 0 |
| Extraction failures | 0 | 0 | 0 |
| Speaker-label accuracy | 85.2 % | 88.9 % | n/a |
| Drug names heard, key terms off / on | 28/31 / 29/31 | 28/31 / 29/31 | n/a |
| Latency p50 / p95: STT (diarized batch job, 4 in parallel) | 13.95 s / 34.15 s | 10.8 s / 28.5 s | n/a |
| Latency p50 / p95: structure() | 4.36 s / 6.84 s | 3.3 s / 6.6 s | 4.4 s / 6.9 s |

**The regression gate FAILED on this run:** `drug_exact` fell from 96.8 to 93.5 (one more drug name misheard by the speech model: 93.5% of 31). Nothing between the two runs touches speech recognition, so this is run-to-run variation in the STT (the same audio does not always give the same transcript), not a code regression; the failed gate is kept in the committed report on purpose. Treat differences of a few points between runs as noise: two runs of the same audio gave 91.5 and 90.9 overall.

### Single-consultation latency (measured by hand, serial, no parallel jobs, 2026-11-03)

Real calls, REST speech-to-text (no diarization), clips S1, S2, S3: speech-to-text 6.2, 0.7, 1.0 s; extraction 5.7, 3.0, 4.5 s; red flags under 0.01 s; summary 0.5, 1.0, 0.8 s; speech 8.1, 6.4, 11.9 s. **Capture to filled record: 11.9, 3.7, 5.5 s. To a spoken summary: 20.5, 11.1, 18.1 s.** STT time varies a lot between runs (S1 took 1.5 s in an earlier run). Source: `docs/DECISIONS.md`, M13 entry. Not part of `latest.json`.

### What the audio runs showed (read before quoting anything)

- **Dose exact match is low (58%) mostly because of formatting.** The STT writes "500 milligram" for a script that said "500mg" and the SPEC says doses are kept "exactly as spoken". It is also a gap in the summary post-check, which only recognizes mg, mcg, g and ml. A deterministic dose normalizer is proposed in `docs/DECISIONS.md` and **not applied**.
- **A real wrong-drug error:** in E06 the STT wrote "Glycopyrrolate" for "Glimepiride" in both runs. No automatic check catches this (the name is literally in the transcript). The clinician review step is the mitigation.
- **Key terms:** one more drug name heard with them on (29 vs 28 of 31) in both runs. That is within noise; no improvement is claimed.
- **Latency:** STT p95 in the harness is above the 20 s target because four batch jobs ran in parallel; see the serial numbers above for one consultation.
- **Speaker labels:** 85 to 89% of reference turns got the right role (heuristic: whoever states drugs and doses is the clinician).
- Red-flag results come from the deterministic rules over what was extracted. Expected flags were hand-written from the rule table. A text-mode run once missed a SpO2 value (recall 92.9), so a missed vital means a missed alert.

### How the metrics are defined

- Facts are matched one-to-one inside each group; F1 is micro-averaged. Complaints and advice match on synonyms or a key word (for example "Eat less salt" counts for "low salt"), vitals, drug names and doses must match exactly after removing spaces, durations and follow-ups need the same number and unit. Frequency is not scored.
- **Hallucination** = an unverified (no matching transcript quote) drug, dose, vital, diagnosis or patient detail. A wrong word that the STT really produced is not a hallucination by this definition. Unverified complaints, advice and timing (translated by the model) are listed in the JSON but not counted.
- N and F scenarios repeat earlier scripts with noise (10 dB SNR) or fast speech (pace 1.4).
