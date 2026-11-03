import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import card
import db
import main
import mock_data
from schemas import ReferralRequest, SignoffRequest


def signed(sid):
    return main.sign_off(SignoffRequest(record=mock_data.scenario_record(sid), clinician_name='Dr Test'))


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')


def test_unconfirmed_referral_is_400():
    for confirmed in (False,):
        with pytest.raises(HTTPException) as e:
            main.referral(ReferralRequest(record=mock_data.scenario_record('S2'), confirmed=confirmed))
        assert e.value.status_code == 400
    assert db.list_tickets() == [] and db.list_records() == []


def test_confirmed_referral_creates_and_persists_ticket():
    t = main.referral(ReferralRequest(record=signed('S2')['record'], confirmed=True))
    assert t['destination'] == 'District Hospital' and t['ticket_id'].startswith('T-')
    assert {f['rule_id'] for f in t['payload']['red_flags']} == {'RF_SEPSIS', 'RF_HYPOTENSION'}
    saved = db.list_tickets()
    assert saved[0]['ticket_id'] == t['ticket_id'] and saved[0]['payload']['vitals']['bp'] == '90/60'


def test_referral_links_an_already_saved_record():
    s = signed('S2')
    main.referral(ReferralRequest(record=s['record'], confirmed=True, record_id=s['id']))
    assert len(db.list_records()) == 1 and db.list_tickets()[0]['record_id'] == s['id']


def test_records_persist_newest_first():
    a, b = signed('S1')['id'], signed('S3')['id']
    rows = main.records()
    assert [r['id'] for r in rows] == [b, a]
    assert rows[1]['record']['prescription'][0]['drug'] == 'Metoprolol'


def test_card_places_medicines_only_where_the_clinician_said():
    grid, other = card.slots(mock_data.scenario_record('S1'))
    assert [n for n, _ in grid['morning']] == ['Metoprolol 50mg']
    assert [n for n, _ in grid['night']] == ['Amlodipine 5mg'] and grid['afternoon'] == [] and other == []
    grid, other = card.slots(mock_data.scenario_record('S3'))   # 'morning and evening, after meals'
    assert grid['morning'] and grid['night'] and not other


def test_card_unspecified_time_goes_to_as_directed():
    rec = mock_data.scenario_record('S1')
    rec.prescription[0].timing = ''
    rec.prescription[0].frequency = 'twice daily'
    grid, other = card.slots(rec)
    assert grid['morning'] == [] and other and other[0][0] == 'Metoprolol 50mg'


def test_card_html_renders_and_escapes():
    rec = mock_data.scenario_record('S1')
    rec.patient.name = '<script>alert(1)</script>'
    html = card.render_card(rec)
    assert '<script>' not in html and '&lt;script&gt;' in html
    for text in ('Metoprolol 50mg', 'Amlodipine 5mg', 'Morning', 'Afternoon', 'Evening / Night', 'Eat less salt',
                 'go to the hospital immediately', 'Clinician must review', 'font-size:28px'):
        assert text in html
    assert render_ok(html)


def render_ok(html):
    return html.startswith('<!doctype html>') and html.rstrip().endswith('</html>') and html.count('<table>') == 1
