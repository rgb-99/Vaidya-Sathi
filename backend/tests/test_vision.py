import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

import config
import main
import mock_data
import sarvam_client
import vision
from schemas import ClinicalRecord, ReconcileRequest, RxItem

PAYLOAD = {'result': {'medicines': [{'drug': 'metoprolol', 'dose': '50mg', 'frequency': '1 morning', 'duration': '30 days'},
                                    {'drug': 'Amlodipine', 'dose': '5mg'}]},
           'annotations': {'medicines': [{'drug': {'confidence': 1}, 'dose': {'confidence': 0.8}}, {'drug': {'confidence': 0.6}}]}}


def fake_status(*statuses):
    it = iter(statuses)
    return lambda job: next(it)


# ---- polling
def test_poll_returns_when_completed(monkeypatch):
    monkeypatch.setattr(sarvam_client, 'doc_status', fake_status('pending', 'running', 'completed'))
    slept = []
    vision.poll('j', sleep=slept.append)
    assert slept == [1.0, 2.0]   # backoff grows


def test_poll_failure_is_a_502_error(monkeypatch):
    monkeypatch.setattr(sarvam_client, 'doc_status', fake_status('pending', 'failed'))
    with pytest.raises(vision.VisionError) as e:
        vision.poll('j', sleep=lambda s: None)
    assert e.value.status_code == 502


def test_poll_times_out(monkeypatch):
    monkeypatch.setattr(sarvam_client, 'doc_status', lambda j: 'pending')
    t = [0.0]
    def sleep(s): t[0] += s
    with pytest.raises(vision.VisionError) as e:
        vision.poll('j', timeout=10, sleep=sleep, clock=lambda: t[0])
    assert e.value.status_code == 504 and t[0] <= 10


# ---- result parsing
def test_parse_normalizes_drug_names_and_reports_min_confidence():
    items = vision.parse_result(PAYLOAD)
    assert items[0] == {'drug': 'Metoprolol', 'dose': '50mg', 'frequency': '1 morning', 'duration': '30 days', 'confidence': 0.8}
    assert items[1]['confidence'] == 0.6 and items[1]['frequency'] == ''


@pytest.mark.parametrize('bad', [{}, {'result': None}, {'result': {'medicines': 'x'}}, {'result': {'medicines': []}},
                                 {'result': {'medicines': [{'dose': '5mg'}, 'junk', None]}}])
def test_malformed_results_raise_instead_of_returning_an_empty_list(bad):
    with pytest.raises(vision.VisionError):
        vision.parse_result(bad)


def test_unusable_rows_are_skipped_but_good_rows_survive():
    items = vision.parse_result({'result': {'medicines': [{'dose': '1'}, {'drug': 'Aspirin', 'dose': '75mg'}, 7]}})
    assert [i['drug'] for i in items] == ['Aspirin'] and items[0]['confidence'] is None


# ---- full flow with Sarvam mocked
def patch_sarvam(monkeypatch, payload=PAYLOAD, statuses=('completed',)):
    monkeypatch.setattr(config, 'MOCK_MODE', False)
    monkeypatch.setattr(sarvam_client, 'doc_extract_start', lambda *a: 'job-1')
    monkeypatch.setattr(sarvam_client, 'doc_status', fake_status(*statuses))
    monkeypatch.setattr(sarvam_client, 'doc_results', lambda j: payload)
    monkeypatch.setattr(vision.time, 'sleep', lambda s: None)


def test_job_flow_completed(monkeypatch):
    patch_sarvam(monkeypatch, statuses=('pending', 'completed'))
    jid = vision.start('rx.png', b'\x89PNGdata', background=False)
    job = vision.status(jid)
    assert job['status'] == 'completed' and [i['drug'] for i in job['items']] == ['Metoprolol', 'Amlodipine']


def test_job_flow_failure_is_reported_not_raised(monkeypatch):
    patch_sarvam(monkeypatch, statuses=('failed',))
    job = vision.status(vision.start('rx.png', b'x', background=False))
    assert job['status'] == 'failed' and 'could not read' in job['error']


def test_job_flow_malformed_payload_fails_cleanly(monkeypatch):
    patch_sarvam(monkeypatch, payload={'result': {'medicines': 'oops'}})
    assert vision.status(vision.start('rx.png', b'x', background=False))['status'] == 'failed'


def test_sarvam_errors_become_a_failed_job(monkeypatch):
    patch_sarvam(monkeypatch)
    def boom(*a):
        raise sarvam_client.SarvamError('Sarvam rejected the API key.')
    monkeypatch.setattr(sarvam_client, 'doc_extract_start', boom)
    assert 'API key' in vision.status(vision.start('rx.png', b'x', background=False))['error']


def test_file_validation():
    for name, data, code in (('rx.txt', b'x', 400), ('rx.png', b'', 400), ('rx.png', b'x' * (vision.MAX_BYTES + 1), 413)):
        with pytest.raises(vision.VisionError) as e:
            vision.check_file(name, data)
        assert e.value.status_code == code
    assert vision.check_file('A.JPG', b'x') == 'image/jpeg'


def test_vision_flag_gates_the_routes(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_VISION', False)
    with pytest.raises(HTTPException) as e:
        main.prescription_photo_result('x')
    assert e.value.status_code == 503 and main.features()['vision'] is False


def test_mock_mode_returns_canned_items_without_network(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    monkeypatch.setattr(sarvam_client, 'doc_status', lambda j: pytest.fail('network'))
    items = vision.read_prescription('rx2.png', b'x')
    assert [i['drug'] for i in items] == ['Metformin', 'Atorvastatin']


# ---- reconciliation (F26)
def today(*rows):
    return ClinicalRecord(prescription=[RxItem(drug=d, dose=ds) for d, ds in rows])


OLD = [{'drug': 'Metoprolol', 'dose': '50mg', 'confidence': 0.9}, {'drug': 'Amlodipine', 'dose': '5mg', 'confidence': 0.7},
       {'drug': 'Aspirin', 'dose': '75mg', 'confidence': 1.0}]


def by_drug(lines):
    return {l['drug']: l for l in lines}


def test_reconcile_new_stopped_changed_and_unchanged():
    lines = by_drug(vision.reconcile(OLD, today(('Metoprolol', '50 mg'), ('Amlodipine', '10mg'), ('Metformin', '500mg'))))
    assert lines['Metoprolol']['status'] == 'unchanged'                      # spacing in the dose is ignored
    assert lines['Amlodipine'] == {'status': 'dose_changed', 'drug': 'Amlodipine', 'old_dose': '5mg', 'new_dose': '10mg', 'confidence': 0.7}
    assert lines['Aspirin']['status'] == 'stopped' and lines['Aspirin']['confidence'] == 1.0
    assert lines['Metformin']['status'] == 'new' and lines['Metformin']['confidence'] is None


def test_reconcile_matches_misspelled_names_through_the_formulary():
    lines = vision.reconcile([{'drug': 'Metaprolol', 'dose': '50mg'}], today(('metoprolol', '50mg')))
    assert [l['status'] for l in lines] == ['unchanged']


def test_reconcile_empty_cases_and_nothing_is_merged():
    assert vision.reconcile([], today()) == []
    rec = today(('Aspirin', '75mg'))
    before = rec.model_dump()
    assert [l['status'] for l in vision.reconcile([], rec)] == ['new'] and rec.model_dump() == before
    assert [l['status'] for l in vision.reconcile(OLD, today())] == ['stopped'] * 3


def test_reconcile_route():
    out = main.reconcile(ReconcileRequest(record=today(('Aspirin', '75mg')), previous=OLD[2:]))
    assert out['lines'][0]['status'] == 'unchanged'
