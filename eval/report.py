"""Writes eval reports and applies the regression gate."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADLINE = ['overall_f1', 'drug_exact', 'dose_exact', 'redflag_precision', 'redflag_recall']
MAX_DROP_POINTS = 2.0


def latest_path():
    return ROOT / 'reports' / 'latest.json'


def load_latest():
    p = latest_path()
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def gate(report, previous):
    """Reasons the run must fail: any hallucination, or a headline metric down by more than 2 points."""
    failures = []
    if report['metrics']['hallucinations'] > 0:
        failures.append(f"hallucinations = {report['metrics']['hallucinations']} (must be 0)")
    prev = (previous or {}).get('metrics')
    if prev and previous.get('mode') == report['mode']:   # only compare like with like
        for k in HEADLINE:
            if prev.get(k) is not None and report['metrics'].get(k) is not None and report['metrics'][k] < prev[k] - MAX_DROP_POINTS:
                failures.append(f"{k} dropped {prev[k]:.1f} -> {report['metrics'][k]:.1f}")
    return failures


def write(report):
    """Timestamped copy in eval/results/ (git-ignored) and eval/reports/latest.json (committed, with the previous run's metrics)."""
    prev = load_latest()
    report['previous'] = {'run_id': prev['run_id'], 'mode': prev['mode'], 'metrics': prev['metrics']} if prev else None
    (ROOT / 'results').mkdir(exist_ok=True)
    (ROOT / 'reports').mkdir(exist_ok=True)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    (ROOT / 'results' / f"{report['run_id']}.json").write_text(text, encoding='utf-8')
    latest_path().write_text(text, encoding='utf-8')
    return latest_path()


def run_id():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
