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

Committed report: `eval/reports/latest.json`, run `20261103T144437Z`, **audio mode** (Bulbul speech -> Saaras `codemix` with diarization -> extraction -> red flags), **32 synthetic scenarios**. All audio is synthetic speech (clean TTS, noise and fast variants included), not real clinic audio.

| Metric | Audio mode (this report) | Text mode (earlier run `20261103T143616Z`, scripts straight to extraction) |
| --- | --- | --- |
| Overall field F1 | 91.5 % | 98.8 % |
| Drug name exact match | 96.8 % | 100 % |
| Dose exact match | 58.1 % | 100 % |
| Red-flag precision / recall | 100.0 % / 100.0 % | 100 % / 100 % |
| Hallucinations | 0 | 0 |
| Extraction failures | 0 | 0 |
| Speaker-label accuracy | 88.9 % | n/a |
| Drug names heard, key terms off / on | 28/31 / 29/31 | n/a |
| Latency p50 / p95: STT (diarized batch job) | 10.78 s / 28.54 s | n/a |
| Latency p50 / p95: structure() | 3.29 s / 6.61 s | 4.4 s / 6.9 s |

The text-mode JSON is not committed (`eval/results/` is git-ignored); its numbers are recorded here and in `docs/DECISIONS.md`.

### What the audio run showed (read before quoting anything)

- **Dose exact match is low (58%) mostly because of formatting.** The STT writes "500 milligram" for a script that said "500mg" and the SPEC says doses are kept "exactly as spoken". It is also a gap in the summary post-check, which only recognizes mg, mcg, g and ml. A deterministic dose normalizer is proposed in `docs/DECISIONS.md` and **not applied**.
- **A real wrong-drug error:** in E06 the STT wrote "Glycopyrrolate" for "Glimepiride". No automatic check catches this (the name is literally in the transcript). The clinician review step is the mitigation.
- **Key terms:** one more drug name heard with them on (29 vs 28 of 31). One name is within noise on synthetic audio; no improvement is claimed.
- **Latency:** STT p95 is above the 20 s end-to-end target. These runs used 4 parallel batch jobs per run, so a single consultation can be faster; not measured separately.
- **Speaker labels:** 88.9% of reference turns got the right role (heuristic: whoever states drugs and doses is the clinician).
- Red-flag results come from the deterministic rules over what was extracted. Expected flags were hand-written from the rule table.

### How the metrics are defined

- Facts are matched one-to-one inside each group; F1 is micro-averaged. Complaints and advice match on synonyms or a key word (for example "Eat less salt" counts for "low salt"), vitals, drug names and doses must match exactly after removing spaces, durations and follow-ups need the same number and unit. Frequency is not scored.
- **Hallucination** = an unverified (no matching transcript quote) drug, dose, vital, diagnosis or patient detail. Unverified complaints, advice and timing (translated by the model) are listed in the JSON but not counted.
- N and F scenarios repeat earlier scripts with noise (10 dB SNR) or fast speech (pace 1.4).
