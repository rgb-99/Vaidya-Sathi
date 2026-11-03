import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mock_data
from schemas import ClinicalRecord, RedFlag


def test_empty_record_validates():
    r = ClinicalRecord()
    assert r.prescription == [] and r.vitals.bp == '' and r.patient.name == ''


def test_partial_record_validates():
    r = ClinicalRecord.model_validate({'vitals': {'bp': '150/95'}, 'chief_complaints': ['headache']})
    assert r.vitals.bp == '150/95' and r.vitals.temp == ''


def test_extra_fields_are_ignored():
    r = ClinicalRecord.model_validate({'diagnosis': 'x', 'unknown_field': 1})
    assert r.diagnosis == 'x'


def test_fenced_json_fails_gracefully_until_stripped():
    fenced = '```json\n{"diagnosis": "x"}\n```'
    with pytest.raises(ValidationError):
        ClinicalRecord.model_validate_json(fenced)
    stripped = fenced.strip('`').removeprefix('json').strip()
    assert ClinicalRecord.model_validate(json.loads(stripped)).diagnosis == 'x'


def test_red_flag_severity_is_restricted():
    with pytest.raises(ValidationError):
        RedFlag(rule_id='X', title='t', severity='critical', matched_inputs=[], action_text='a')


def test_defaults_are_not_shared_between_instances():
    a, b = ClinicalRecord(), ClinicalRecord()
    a.patient.name = 'Changed'
    assert b.patient.name == ''


@pytest.mark.parametrize('sid', ['S1', 'S2', 'S3'])
def test_mock_scenarios_validate(sid):
    assert mock_data.scenario_record(sid).language_detected


def test_s2_has_red_flags_and_others_do_not():
    ids = {f.rule_id for f in mock_data.scenario_record('S2').red_flags}
    assert ids == {'RF_SEPSIS', 'RF_HYPOTENSION'}
    assert mock_data.scenario_record('S1').red_flags == []
    assert mock_data.scenario_record('S3').red_flags == []
