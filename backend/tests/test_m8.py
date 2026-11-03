import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

import config
import db
import formulary
import llm
import main
import mock_data
import sarvam_client
import voice
from schemas import SignoffRequest, SummaryRequest, Utterance


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')
    monkeypatch.setattr(config, 'MOCK_MODE', False)


def entry(spk, text, t=0.0):
    return {'speaker_id': spk, 'transcript': text, 'start_time_seconds': t, 'end_time_seconds': t + 3}


DIALOG = [entry('2', 'Doctor, मला डोके दुखतंय. Aspirin घेऊ का?'), entry('1', 'BP 150/95 आहे. हे Metoprolol 50 mg सकाळी एक गोळी घ्या 30 दिवस.', 4),
          entry('2', 'ठीक आहे Doctor.', 9)]


# ---- diarization roles

def test_speaker_stating_drugs_and_doses_is_the_clinician_regardless_of_id_order():
    turns = voice.assign_roles(DIALOG)
    assert [u.speaker for u in turns] == ['patient', 'clinician', 'patient']
    assert turns[1].start_s == 4 and turns[0].id == 'u1'


def test_roles_follow_content_not_speaker_numbering():
    swapped = [entry('1', e['transcript'], e['start_time_seconds']) if e['speaker_id'] == '2' else entry('2', e['transcript'], e['start_time_seconds']) for e in DIALOG]
    assert [u.speaker for u in voice.assign_roles(swapped)] == ['patient', 'clinician', 'patient']


def test_single_speaker_marks_everything_unknown():
    assert {u.speaker for u in voice.assign_roles([entry('0', 'Metoprolol 50 mg घ्या'), entry('0', 'ठीक')])} == {'unknown'}


def test_no_clear_winner_marks_unknown():
    assert {u.speaker for u in voice.assign_roles([entry('0', 'नमस्कार'), entry('1', 'नमस्कार')])} == {'unknown'}


def test_diarized_transcribe_returns_labelled_turns(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'ENABLE_DIARIZATION', True)
    monkeypatch.setattr(sarvam_client, 'stt_diarized', lambda p, **k: {'transcript': 'x', 'language': 'mr-IN', 'entries': DIALOG})
    monkeypatch.setattr(voice, 'probe_duration', lambda p: 12.0)
    out = voice.transcribe(b'RIFFxxxx', 'a.wav')
    assert out['language'] == 'mr-IN' and [u.speaker for u in out['utterances']] == ['patient', 'clinician', 'patient']


def test_diarization_failure_falls_back_with_a_notice(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_DIARIZATION', True)
    def boom(p, **k):
        raise sarvam_client.SarvamError('down')
    monkeypatch.setattr(sarvam_client, 'stt_diarized', boom)
    monkeypatch.setattr(sarvam_client, 'stt', lambda p, **k: {'transcript': 'plain', 'language': 'hi-IN'})
    monkeypatch.setattr(voice, 'probe_duration', lambda p: 12.0)
    out = voice.transcribe(b'RIFFxxxx', 'a.wav')
    assert out['transcript'] == 'plain' and out['utterances'] == [] and 'unavailable' in out['notice']


def test_mock_diarization_gives_labelled_turns(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    monkeypatch.setattr(config, 'ENABLE_DIARIZATION', True)
    turns = voice.transcribe(b'x', 'S1.wav')['utterances']
    assert {u.speaker for u in turns} == {'clinician', 'patient'} and any('Metoprolol' in u.text for u in turns)


# ---- role-aware extraction

PATIENT_ASKS_ASPIRIN = ('{"patient":{},"chief_complaints":["headache"],"vitals":{"bp":"150/95"},'
                        '"prescription":[{"drug":"Aspirin","dose":""},{"drug":"Metoprolol","dose":"50 mg","frequency":"once daily","timing":"morning","duration":"30 days"}],'
                        '"advice":[],"follow_up":"","evidence":[]}')


def test_drug_said_only_by_the_patient_never_lands_in_the_prescription(monkeypatch):
    seen = {}
    def chat(model, system, user, **k):
        seen.update(system=system, user=user)
        return PATIENT_ASKS_ASPIRIN   # the LLM ignores the instruction on purpose
    monkeypatch.setattr(sarvam_client, 'chat', chat)
    rec = llm.structure('ignored', voice.assign_roles(DIALOG))
    assert [r.drug for r in rec.prescription] == ['Metoprolol']
    assert any('Aspirin' in w and 'not said by the clinician' in w for w in rec.warnings)
    assert 'Clinician: BP 150/95' in seen['user'] and 'Patient: Doctor' in seen['user']
    assert 'ONLY from Clinician turns' in seen['system']


def test_without_roles_the_role_free_prompt_is_used(monkeypatch):
    seen = {}
    monkeypatch.setattr(sarvam_client, 'chat', lambda m, s, u, **k: seen.update(system=s, user=u) or PATIENT_ASKS_ASPIRIN)
    rec = llm.structure('BP check kela', voice.assign_roles([entry('0', 'Metoprolol 50 mg'), entry('0', 'ok')]))
    assert 'ONLY from Clinician turns' not in seen['system'] and seen['user'] == 'BP check kela'
    assert len(rec.prescription) == 2 and rec.utterances[0].id == 'u1'


def test_provenance_points_to_the_utterance_that_holds_the_quote(monkeypatch):
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: PATIENT_ASKS_ASPIRIN)
    rec = llm.structure('x', voice.assign_roles(DIALOG))
    assert rec.provenance['vitals.bp'].source_utterance_ids == ['u2']


# ---- key terms

def test_key_terms_respect_the_documented_limits():
    terms = formulary.key_terms()
    assert 0 < len(terms) <= 50 and all(len(t) <= 64 for t in terms) and len(set(terms)) == len(terms)


@pytest.mark.parametrize('flag', [True, False])
def test_keyterms_passed_to_stt_only_when_enabled(flag, monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_KEYTERMS', flag)
    seen = {}
    monkeypatch.setattr(sarvam_client, 'stt', lambda p, **k: seen.update(k) or {'transcript': '', 'language': ''})
    voice._stt('x.wav')
    assert ('keyterms' in seen) is flag


# ---- language breadth

def test_languages_endpoint_lists_only_voiced_languages(monkeypatch):
    monkeypatch.setitem(config.TTS_SPEAKERS, 'hi-IN', '')
    codes = {l['code'] for l in main.languages()}
    assert 'hi-IN' not in codes and {'ta-IN', 'bn-IN', 'te-IN'} <= codes and 'ml-IN' not in codes and 'od-IN' not in codes


def test_unsupported_language_is_rejected():
    from schemas import ClinicalRecord
    s = main.sign_off(SignoffRequest(record=ClinicalRecord(), clinician_name='Dr T'))['record']
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.summary(SummaryRequest(record=s, language='xx-IN')))
    assert e.value.status_code == 400


def test_other_language_summary_uses_llm_and_its_own_voice(monkeypatch):
    rec = mock_data.scenario_record('S1')
    tamil = 'காலை Metoprolol 50mg ஒரு மாத்திரை. இரவு Amlodipine 5mg ஒரு மாத்திரை.'
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: tamil)
    text, fb = llm.summarize(rec, 'ta-IN')
    assert not fb and text == tamil and llm.spoken_language('ta-IN', fb) == 'ta-IN'


def test_other_language_template_fallback_is_english_and_says_so(monkeypatch):
    rec = mock_data.scenario_record('S1')
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: 'bad Aspirin')
    text, fb = llm.summarize(rec, 'ta-IN')
    assert fb and 'Metoprolol' in text and llm.spoken_language('ta-IN', fb) == 'en-IN'
