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

Run `20261103T141228Z`, **text mode**, **32 synthetic scenarios** (scripts only: no audio and no STT in this run, so STT errors, diarization and key terms are not measured yet). Full detail: `eval/reports/latest.json`.

| Metric | Value |
| --- | --- |
| Overall field F1 | 95.6 % |
| Drug name exact match | 100.0 % |
| Dose exact match | 100.0 % |
| Red-flag precision / recall | 100.0 % / 100.0 % |
| Hallucinations | 0 |
| Extraction failures | 0 of 32 |
| Latency structure() p50 / p95 | 4.21 s / 7.59 s |
| Speaker accuracy, key-term A/B | not run (needs audio mode) |

Per-field F1: complaints 97.3, vitals 100.0, drug 98.4, dose 98.4, timing 88.9, duration 92.1, advice 93.1, follow_up 95.0.

### How to read these numbers

- **Metric definitions.** Facts are matched one-to-one inside each group. F1 is micro-averaged. Complaints and advice are matched on synonyms or a key word (for example "Eat less salt" counts for "low salt") because the model paraphrases; vitals, drug names and doses must match exactly after removing spaces; durations and follow-ups must have the same number and unit. Frequency is not scored. Red-flag expected sets were written by hand from the SPEC section 9 table, not produced by the engine.
- **Hallucination** here means an unverified (no matching transcript quote) drug, dose, vital, diagnosis or patient detail. Unverified complaints, advice and timing (translated by the model) are reported in the JSON but not counted.
- **N and F scenarios** repeat earlier scripts so that, in audio mode, the same text is heard with noise (10 dB SNR) or fast speech (pace 1.4). In text mode they are duplicates, so text-mode numbers weigh those scripts twice.
- **Known failure (about 1 in 32 runs of a scenario):** with the same input the model occasionally leaves complaints, advice, timing and follow-up in the original script (Marathi) instead of translating to English; extraction still works for drugs, doses and vitals. It hit F01 in one run and E03 in the next, so it is not tied to a script. A fix is proposed in `docs/DECISIONS.md`, not applied.
- The scripts are clean, written text and the model has no speech-recognition errors to cope with, so these numbers are an upper bound for the full pipeline.
