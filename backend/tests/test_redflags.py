import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mock_data
import redflags
from schemas import ClinicalRecord, Vitals, Utterance


def rec(complaints=(), transcript='', **vitals):
    return ClinicalRecord(chief_complaints=list(complaints), vitals=Vitals(**vitals),
                          utterances=[Utterance(id='u1', text=transcript)] if transcript else [])


def ids(r, transcript=''):
    return {f.rule_id for f in redflags.check(r, transcript)}


def test_s2_triggers_sepsis_and_hypotension():
    flags = redflags.check(mock_data.scenario_record('S2'), mock_data.SCENARIOS['S2']['transcript'])
    assert {f.rule_id for f in flags} == {'RF_SEPSIS', 'RF_HYPOTENSION'}
    sepsis = next(f for f in flags if f.rule_id == 'RF_SEPSIS')
    assert sepsis.severity == 'urgent' and sepsis.matched_inputs == ['temp 102F', 'BP 90/60', 'pulse 118', 'breathlessness keyword']


def test_s1_and_s3_trigger_nothing():
    for sid in ('S1', 'S3'):
        assert redflags.check(mock_data.scenario_record(sid), mock_data.SCENARIOS[sid]['transcript']) == []


def test_empty_record_triggers_nothing():
    assert redflags.check(ClinicalRecord()) == []


def test_missing_inputs_never_trigger():
    assert ids(rec(temp='102')) == set()                     # fever alone is not sepsis
    assert ids(rec(temp='102', pulse='118')) == set()        # no breathlessness
    assert ids(rec(bp='abc', pulse='x')) == set()


@pytest.mark.parametrize('bp,expected', [('91/60', False), ('90/60', True), ('89/60', True)])
def test_hypotension_boundary(bp, expected):
    assert ('RF_HYPOTENSION' in ids(rec(bp=bp))) is expected


@pytest.mark.parametrize('temp,expected', [('100.3', False), ('100.4', True), ('102 degree', True), ('102F', True)])
def test_sepsis_temperature_boundary(temp, expected):
    r = rec(['breathlessness'], temp=temp, pulse='110')
    assert ('RF_SEPSIS' in ids(r)) is expected


def test_celsius_values_are_converted():
    assert redflags.parse_temp_f('39') == pytest.approx(102.2)
    assert 'RF_HIGH_FEVER' in ids(rec(temp='39.5'))


def test_sepsis_via_resp_rate_and_systolic():
    assert 'RF_SEPSIS' in ids(rec(temp='101', bp='95/60', resp_rate='24'))
    assert 'RF_SEPSIS' not in ids(rec(temp='101', bp='95/60', resp_rate='22'))


@pytest.mark.parametrize('vitals,rule,expected', [
    ({'bp': '180/90'}, 'RF_HYPERTENSIVE', True), ({'bp': '179/119'}, 'RF_HYPERTENSIVE', False),
    ({'bp': '150/120'}, 'RF_HYPERTENSIVE', True),
    ({'spo2': '91'}, 'RF_HYPOXIA', True), ({'spo2': '92'}, 'RF_HYPOXIA', False),
    ({'temp': '103'}, 'RF_HIGH_FEVER', True), ({'temp': '102.9'}, 'RF_HIGH_FEVER', False),
    ({'sugar': '301'}, 'RF_HYPERGLYCEMIA', True), ({'sugar': '300'}, 'RF_HYPERGLYCEMIA', False),
])
def test_threshold_rules(vitals, rule, expected):
    assert (rule in ids(rec(**vitals))) is expected


def test_severities():
    flags = {f.rule_id: f.severity for f in redflags.check(rec(['chest pain'], temp='104', sugar='350', spo2='90'))}
    assert flags['RF_CHEST_PAIN'] == flags['RF_HYPOXIA'] == 'urgent'
    assert flags['RF_HIGH_FEVER'] == flags['RF_HYPERGLYCEMIA'] == 'warning'


@pytest.mark.parametrize('text', ['chest pain', 'Chhati dukhna', 'छातीत दुखतंय', 'सीने में दर्द'])
def test_chest_pain_keywords_trilingual(text):
    assert 'RF_CHEST_PAIN' in ids(rec(), text)


def test_dehydration_needs_symptom_and_circulation_sign():
    assert 'RF_DEHYDRATION' in ids(rec(['vomiting'], pulse='110'))
    assert 'RF_DEHYDRATION' in ids(rec(['loose motion'], bp='95/60'))
    assert 'RF_DEHYDRATION' not in ids(rec(['vomiting'], pulse='80', bp='120/80'))
    assert 'RF_DEHYDRATION' not in ids(rec(pulse='120'))


def test_keywords_need_word_boundaries():
    assert 'RF_DEHYDRATION' not in ids(rec(['multivitamin'], pulse='120'))


def test_transcript_symptoms_count_and_survive_roundtrip():
    r = rec(temp='102', bp='90/60', pulse='118', transcript='breathlessness pan vattoy')
    assert 'RF_SEPSIS' in ids(r)  # via record.utterances, as /redflags receives it after an edit


@pytest.mark.parametrize('s,expected', [('90/60', (90, 60)), ('BP 120 / 80', (120, 80)), ('१२०/८०', (120, 80)), ('abc', None), ('', None)])
def test_parse_bp(s, expected):
    assert redflags.parse_bp(s) == expected


@pytest.mark.parametrize('s,expected', [('102', 102), ('102F', 102), ('102 degree', 102), ('98.6', 98.6), ('x', None), ('', None)])
def test_parse_number(s, expected):
    assert redflags.parse_number(s) == expected


def test_action_and_alert_text_have_no_doses_and_cover_all_languages():
    import re
    for rule, per_lang in redflags.ALERTS.items():
        assert set(per_lang) == {'mr-IN', 'hi-IN', 'en-IN'}
        for text in per_lang.values():
            assert not re.search(r'\d|\bmg\b', text)
    for text in redflags.ACTIONS.values():
        assert not re.search(r'\d|\bmg\b', text)
    flags = redflags.check(mock_data.scenario_record('S2'), 'breathless')
    assert 'hospital' in redflags.alert_text(flags, 'en-IN')
    assert redflags.alert_text(flags, 'xx') == redflags.alert_text(flags, 'en-IN')
