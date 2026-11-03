import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

import config
import db
import ics
import main
import mock_data
import safety
import share
from schemas import ClinicalRecord, RxItem, ShareRequest, SignoffRequest


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    share._hits.clear()


def signed(sid='S1', **edits):
    rec = mock_data.scenario_record(sid)
    rec.patient.name = 'Ramesh Kumar Patil'
    rec.diagnosis = 'Hypertension'
    for k, v in edits.items():
        setattr(rec, k, v)
    out = main.sign_off(SignoffRequest(record=rec, clinician_name='Dr Test'))
    return out['record'], out['id']


def make_share(**kw):
    rec, _ = signed()
    return asyncio.run(main.create_share(ShareRequest(record=rec, language='en-IN', **kw)))


# ---- share page

def test_unsigned_record_cannot_be_shared():
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.create_share(ShareRequest(record=mock_data.scenario_record('S1'), language='en-IN')))
    assert e.value.status_code == 403


def test_share_returns_token_url_qr_and_expiry():
    s = make_share()
    assert len(s['token']) >= 22 and s['url'] == f"{config.PUBLIC_BASE_URL}/share/{s['token']}"
    assert base64.b64decode(s['qr_png_base64'])[:8] == b'\x89PNG\r\n\x1a\n'
    delta = datetime.fromisoformat(s['expires_at']) - datetime.now(timezone.utc)
    assert timedelta(days=config.SHARE_TOKEN_TTL_DAYS - 1) < delta <= timedelta(days=config.SHARE_TOKEN_TTL_DAYS)


def test_tokens_are_128_bit_unique():
    assert len({share.create(mock_data.scenario_record('S1'), 't', '', 'en-IN')['token'] for _ in range(50)}) == 50
    assert len(share.create(mock_data.scenario_record('S1'), 't', '', 'en-IN')['token']) == 22   # 16 bytes, base64url


def test_public_page_shows_schedule_first_name_and_audio_only():
    s = make_share()
    body = json.loads(main.public_share(s['token'], FakeRequest()).body)
    assert body['first_name'] == 'Ramesh' and body['audio_base64'] and body['summary_text']
    assert [m['medicine'] for m in body['schedule']['morning']] == ['Metoprolol 50mg']
    assert body['advice'] == ['Eat less salt']


def test_no_diagnosis_leaks_unless_ticked():
    off = json.loads(main.public_share(make_share()['token'], FakeRequest()).body)
    on = json.loads(main.public_share(make_share(include_diagnosis=True)['token'], FakeRequest()).body)
    assert off['diagnosis'] == '' and on['diagnosis'] == 'Hypertension'
    raw = json.dumps(off)
    for private in ('Kumar', 'Patil', 'Hypertension', '150/95', 'Dr Test', 'signature', 'utterances'):
        assert private not in raw


def test_expired_token_is_404_and_unknown_is_404():
    rec, _ = signed()
    old = datetime.now(timezone.utc) - timedelta(days=config.SHARE_TOKEN_TTL_DAYS + 1)
    token = share.create(rec, 't', '', 'en-IN', now=old)['token']
    assert share.get(token) is None
    for t in (token, 'nope'):
        r = main.public_share(t, FakeRequest())
        assert r.status_code == 404 and r.headers['x-robots-tag'] == 'noindex, nofollow'


def test_public_endpoint_is_rate_limited_and_noindex():
    token = make_share()['token']
    codes = [main.public_share(token, FakeRequest()).status_code for _ in range(share.RATE_LIMIT + 3)]
    assert codes[0] == 200 and codes[-1] == 429 and codes.count(200) == share.RATE_LIMIT
    assert main.public_share(token, FakeRequest('9.9.9.9')).status_code == 200   # another client is unaffected


class FakeRequest:
    def __init__(self, host='1.1.1.1'):
        self.client = type('C', (), {'host': host})()


# ---- reminder file

def test_ics_is_valid_and_repeats_for_the_prescribed_days():
    rec, rid = signed()
    resp = main.schedule_ics(rid)
    text = resp.body.decode()
    assert resp.media_type == 'text/calendar' and text.startswith('BEGIN:VCALENDAR\r\n') and text.endswith('END:VCALENDAR\r\n')
    assert text.count('BEGIN:VEVENT') == text.count('END:VEVENT') == 2
    assert 'SUMMARY:Take Metoprolol 50mg' in text and 'RRULE:FREQ=DAILY;COUNT=30' in text and 'T080000' in text
    assert all(len(l.encode()) <= 75 for l in text.split('\r\n')) and '\n' not in text.replace('\r\n', '')


def test_ics_unsigned_is_403_and_no_duration_means_no_repeat():
    rec = mock_data.scenario_record('S1')
    rid = db.save_record(rec)
    with pytest.raises(HTTPException) as e:
        main.schedule_ics(rid)
    assert e.value.status_code == 403
    rec.prescription[0].duration = ''
    assert 'RRULE' not in ics.build(rec)   # S1's Amlodipine never had a duration either: nothing is invented


def test_ics_escapes_and_folds_long_lines():
    rec = ClinicalRecord(prescription=[RxItem(drug='Metformin', dose='500mg', timing='morning, with; breakfast ' * 8, duration='5 days')])
    text = ics.build(rec)
    assert all(len(l.encode()) <= 75 for l in text.split('\r\n')) and '\\,' in text.replace('\r\n ', '')


# ---- prescription safety checks: one test per rule

def rx(*drugs):
    return ClinicalRecord(prescription=[RxItem(drug=d, dose='1mg') for d in drugs])


def ids(rec, production=False):
    return {w.rule_id for w in safety.check(rec, production)}


def test_rule_duplicate_drug():
    w = safety.check(rx('Metformin', 'metformin'))
    assert [x.rule_id for x in w] == ['SAFE_DUPLICATE_DRUG'] and w[0].severity == 'warning'


def test_rule_same_class_beta_blockers():
    assert 'SAFE_CLASS_BETA_BLOCKER' in ids(rx('Metoprolol', 'Atenolol'))


def test_rule_same_class_arb():
    assert 'SAFE_CLASS_ARB' in ids(rx('Telmisartan', 'Losartan'))


def test_rule_same_class_statin():
    assert 'SAFE_CLASS_STATIN' in ids(rx('Atorvastatin', 'Rosuvastatin'))


def test_rule_same_class_ppi():
    assert 'SAFE_CLASS_PPI' in ids(rx('Pantoprazole', 'omeprazole'))


def test_rule_allergy_match():
    rec = rx('Amoxicillin', 'Cetirizine')
    rec.allergies = ['amoxicilin']        # spelling slip still matches through the formulary
    w = safety.check(rec)
    assert [x.rule_id for x in w] == ['SAFE_ALLERGY'] and 'Amoxicillin' in w[0].matched_inputs


def test_no_false_alarms_and_prescription_is_never_changed():
    rec = rx('Metoprolol', 'Amlodipine', 'Metformin')
    before = rec.model_dump()
    assert safety.check(rec) == [] and rec.model_dump() == before
    assert safety.check(ClinicalRecord()) == []


def test_unreviewed_rules_are_ignored_in_production_mode_only():
    assert 'SAFE_DUPLICATE_DRUG' in ids(rx('Aspirin', 'Aspirin'), production=False)
    assert ids(rx('Aspirin', 'Aspirin'), production=True) == set()
    assert 'not yet reviewed' in safety.check(rx('Aspirin', 'Aspirin'), False)[0].title


def test_dose_limit_table_is_empty_until_cited():
    data = json.loads(safety.RULES_PATH.read_text())
    assert data['max_daily_dose'] == [] and all('source' in r and 'reviewed_by' in r for r in data['rules'])


def test_structure_attaches_safety_warnings():
    rec = asyncio.run(main.structure(main.StructureRequest(transcript=mock_data.SCENARIOS['S1']['transcript'])))
    assert rec.safety_warnings == []
