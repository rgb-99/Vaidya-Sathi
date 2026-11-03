import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analytics
import db
import main
import mock_data
from schemas import BaselineRequest, SignoffRequest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')


def sign(sid, started, demo=False):
    return main.sign_off(SignoffRequest(record=mock_data.scenario_record(sid), clinician_name='Dr T', started_at=started, demo=demo))


def ago(seconds):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def test_nothing_measured_reports_nothing_not_zero():
    s = analytics.summary()
    assert s['consultations'] == 0 and s['mean_minutes_saved'] is None and s['baseline_minutes'] is None and s['language_mix'] == {}


def test_minutes_saved_needs_a_baseline_and_a_measured_duration():
    sign('S1', ago(120))                     # 2 minutes
    assert analytics.summary()['mean_documentation_minutes'] == pytest.approx(2.0, abs=0.1)
    assert analytics.summary()['mean_minutes_saved'] is None       # no baseline yet: no claim
    main.set_baseline(BaselineRequest(minutes=6))
    s = analytics.summary()
    assert s['mean_minutes_saved'] == pytest.approx(4.0, abs=0.1) and s['total_minutes_saved'] == pytest.approx(4.0, abs=0.1)


def test_demo_runs_and_unmeasured_runs_never_count_towards_minutes_saved():
    main.set_baseline(BaselineRequest(minutes=5))
    sign('S1', ago(60))
    sign('S3', ago(10), demo=True)
    sign('S2', '')                           # start time not reported
    sign('S3', 'garbage')
    s = analytics.summary()
    assert (s['consultations'], s['demo_consultations'], s['live_consultations'], s['timed_consultations']) == (4, 1, 3, 1)
    assert s['mean_minutes_saved'] == pytest.approx(4.0, abs=0.1)


def test_implausible_durations_are_not_measured():
    assert analytics.measured_seconds(ago(-3600), ago(0)) is None            # starts in the future
    assert analytics.measured_seconds('2020-01-01T00:00:00+00:00', ago(0)) is None   # years long


def test_counts_of_flags_warnings_and_languages():
    sign('S2', ago(30))      # S2: two urgent red flags, Marathi
    sign('S3', ago(30))      # Hindi, none
    s = analytics.summary()
    assert s['red_flags'] == 2 and s['urgent_red_flags'] == 2 and s['safety_warnings'] == 0
    assert s['language_mix'] == {'mr-IN': 1, 'hi-IN': 1}


def test_a_slower_consultation_shows_negative_savings_honestly():
    main.set_baseline(BaselineRequest(minutes=1))
    sign('S1', ago(300))
    assert analytics.summary()['mean_minutes_saved'] < 0


@pytest.mark.parametrize('minutes', [0, -3, 500])
def test_baseline_must_be_sensible(minutes):
    with pytest.raises(HTTPException) as e:
        main.set_baseline(BaselineRequest(minutes=minutes))
    assert e.value.status_code == 400
