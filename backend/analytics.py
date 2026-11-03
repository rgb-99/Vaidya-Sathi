"""Clinician analytics (F30). Only measured numbers are shown; anything that was not measured is reported as such.

Minutes saved = the typing time the clinician entered once (baseline) minus the measured time from transcript-ready to
sign-off. The start time is reported by the browser, so it is a client-side measurement. Demo runs (picked from the demo
list) are counted separately and never enter the minutes-saved figure."""
from collections import Counter
from datetime import datetime

import db

MAX_PLAUSIBLE_S = 4 * 3600


def measured_seconds(started_at, signed_at):
    """Seconds between two ISO timestamps, or None when missing, unreadable or implausible."""
    try:
        d = (datetime.fromisoformat(signed_at) - datetime.fromisoformat(started_at.replace('Z', '+00:00'))).total_seconds()
    except (ValueError, AttributeError, TypeError):
        return None
    return d if 0 <= d <= MAX_PLAUSIBLE_S else None


def record_consultation(record_id, record, started_at='', demo=False):
    urgent = sum(f.severity == 'urgent' for f in record.red_flags)
    db.save_consultation(record_id, started_at, record.signed_at, measured_seconds(started_at, record.signed_at), demo,
                         record.language_detected or 'unknown', len(record.red_flags), urgent, len(record.safety_warnings))


def baseline_minutes():
    v = db.get_setting('typing_baseline_minutes')
    return float(v) if v else None


def summary():
    rows = db.list_consultations()
    live = [r for r in rows if not r['demo']]
    timed = [r['duration_s'] for r in live if r['duration_s'] is not None]
    base = baseline_minutes()
    mean_min = round(sum(timed) / len(timed) / 60, 2) if timed else None
    saved = [base - s / 60 for s in timed] if base is not None else []
    return {
        'consultations': len(rows), 'demo_consultations': len(rows) - len(live), 'live_consultations': len(live),
        'timed_consultations': len(timed),
        'baseline_minutes': base, 'mean_documentation_minutes': mean_min,
        'mean_minutes_saved': round(sum(saved) / len(saved), 2) if saved else None,
        'total_minutes_saved': round(sum(saved), 2) if saved else None,
        'red_flags': sum(r['red_flags'] for r in rows), 'urgent_red_flags': sum(r['urgent_flags'] for r in rows),
        'safety_warnings': sum(r['safety_warnings'] for r in rows),
        'language_mix': dict(Counter(r['language'] for r in rows)),
        'note': 'Minutes saved uses live consultations only: time from transcript ready to sign-off (browser clock) against the typing baseline you entered.',
    }
