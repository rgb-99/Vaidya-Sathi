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
# Generate synthetic audio (requires SARVAM_API_KEY)
python eval/synthesize_audio.py

# Run the full evaluation
python eval/run_eval.py

# View the report
# Open http://localhost:5173/eval in the browser, or:
cat eval/results/latest.json
```

One command to reproduce all numbers:

```bash
python eval/run_eval.py --all
```

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

_No evaluation runs yet. Run `python eval/run_eval.py` to generate the first report._

