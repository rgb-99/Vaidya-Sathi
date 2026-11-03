import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
import llm
import main
import mock_data
import signoff
from schemas import ReferralRequest, SignoffRequest, SummaryRequest


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')
    monkeypatch.setattr(config, 'MOCK_MODE', True)


def structured(sid):
    return llm.structure(mock_data.SCENARIOS[sid]['transcript'])


def do_sign(sid='S1', name='Dr Test'):
    return main.sign_off(SignoffRequest(record=structured(sid), clinician_name=name))


def status(fn, *a):
    with pytest.raises(HTTPException) as e:
        fn(*a)
    return e.value.status_code


# ---- sign-off is enforced server-side

def test_unsigned_record_is_rejected_by_summary_referral_and_export():
    rec = structured('S2')
    assert status(lambda: asyncio.run(main.summary(SummaryRequest(record=rec, language='en-IN')))) == 403
    assert status(main.referral, ReferralRequest(record=rec, confirmed=True)) == 403
    rid = db.save_record(rec)
    assert status(main.export_record, rid) == 403


def test_forged_signature_fields_are_rejected():
    rec = structured('S1')
    rec.signed_off_by, rec.signed_at, rec.signature = 'Dr Fake', '2026-01-01', 'abc'
    assert not signoff.is_signed(rec)
    assert status(main.referral, ReferralRequest(record=rec, confirmed=True)) == 403


def test_editing_after_signing_invalidates_the_signature():
    s = do_sign('S1')['record']
    assert signoff.is_signed(s)
    s.prescription[0].dose = '500mg'
    assert not signoff.is_signed(s)
    assert status(main.referral, ReferralRequest(record=s, confirmed=True)) == 403


def test_rederived_red_flags_do_not_break_the_signature():
    s = do_sign('S2')['record']
    s.red_flags = []
    assert signoff.is_signed(s)


def test_signed_record_passes_every_gate():
    out = do_sign('S2')
    rec = out['record']
    assert rec.signed_off_by == 'Dr Test' and rec.signed_at
    resp = asyncio.run(main.summary(SummaryRequest(record=rec, language='en-IN')))
    assert resp.text and resp.audio_base64
    assert main.referral(ReferralRequest(record=rec, confirmed=True, record_id=out['id']))['ticket_id']
    assert main.export_record(out['id'])['resourceType'] == 'Bundle'


def test_signoff_needs_a_clinician_name():
    assert status(main.sign_off, SignoffRequest(record=structured('S1'), clinician_name='  ')) == 400


def test_export_unknown_id_is_404():
    assert status(main.export_record, 999) == 404


# ---- said vs inferred

def test_every_said_fact_has_a_verbatim_quote():
    for sid in ('S1', 'S2', 'S3'):
        rec, transcript = structured(sid), mock_data.SCENARIOS[sid]['transcript']
        assert rec.said
        for fact in rec.said:
            path = fact.split(':')[0]
            assert llm._norm(rec.provenance[path].quote) in llm._norm(transcript)


def test_llm_claimed_quote_not_in_transcript_is_rejected():
    rec = mock_data.scenario_record('S1')
    ev = [{'field': 'vitals.bp', 'quote': 'blood pressure is 200/120'}]  # fabricated quote
    llm.attach_evidence(rec, ev, 'Doctor: BP check kela, 150/95 ahe.')
    assert 'vitals.bp: 150/95' in rec.said                     # recovered via the literal sentence
    assert 'blood pressure' not in rec.provenance['vitals.bp'].quote


def test_value_without_any_quote_goes_to_inferred_not_said():
    rec = mock_data.scenario_record('S1')
    llm.attach_evidence(rec, [], 'Doctor: BP check kela, 150/95 ahe.')
    assert any('chief_complaints.0: headache' in x and x.startswith('Unverified') for x in rec.inferred)
    assert not any('headache' in x for x in rec.said)


def test_valid_llm_quote_for_a_translated_value_is_accepted():
    rec = mock_data.scenario_record('S1')
    tr = mock_data.SCENARIOS['S1']['transcript']
    llm.attach_evidence(rec, [{'field': 'chief_complaints.0', 'quote': 'doke dukhtay'}], tr)
    assert 'chief_complaints.0: headache' in rec.said and rec.provenance['chief_complaints.0'].quote == 'doke dukhtay'


def test_few_shot_evidence_quotes_are_verbatim_substrings():
    for sid, fields in llm.EXAMPLE_EVIDENCE.items():
        for field, quote in fields.items():
            assert quote in mock_data.SCENARIOS[sid]['transcript'], (sid, field)


# ---- audit trail and export

def test_provenance_records_model_prompt_version_and_utterance():
    p = structured('S1').provenance['vitals.bp']
    assert p.source_utterance_ids == ['u1'] and p.model == config.LLM_MODEL and p.prompt_version == llm.PROMPT_VERSION


def test_export_bundle_contains_resources_provenance_and_honest_label():
    out = do_sign('S1')
    b = main.export_record(out['id'])
    kinds = [e['resource']['resourceType'] for e in b['entry']]
    assert kinds[:2] == ['Patient', 'Encounter'] and 'Observation' in kinds and kinds.count('MedicationRequest') == 2
    rx = next(e['resource'] for e in b['entry'] if e['resource']['resourceType'] == 'MedicationRequest')
    assert rx['requester']['display'] == 'Dr Test' and rx['audit'][0]['quote'] and rx['audit'][0]['prompt_version']
    label = b['meta']['tag'][0]['display']
    assert 'FHIR-inspired' in label and 'Not FHIR-compliant' in label
