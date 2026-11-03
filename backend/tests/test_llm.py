import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import formulary
import llm
import sarvam_client


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)


def fake_chat(*outputs):
    it = iter(outputs)
    calls = []

    def chat(model, system, user, **kw):
        calls.append(user)
        return next(it)
    return chat, calls


GOOD = '{"vitals": {"bp": "150/95"}, "prescription": [{"drug": "metoprolol", "dose": "50mg"}], "extra": 1}'


def test_parse_json_handles_fences_and_reasoning():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {'a': 1}
    assert llm.parse_json('<think>hmm {x}</think>Here: {"a": 1} done') == {'a': 1}
    with pytest.raises(ValueError):
        llm.parse_json('no json here')


def test_structure_validates_normalizes_and_ignores_extras(monkeypatch):
    chat, _ = fake_chat('```json\n' + GOOD + '\n```')
    monkeypatch.setattr(sarvam_client, 'chat', chat)
    r = llm.structure('x')
    assert r.vitals.bp == '150/95' and r.vitals.temp == ''
    assert r.prescription[0].drug == 'Metoprolol'  # formulary normalization


def test_llm_cannot_inject_red_flags(monkeypatch):
    bad = '{"red_flags": [{"rule_id": "X", "title": "t", "severity": "urgent", "matched_inputs": [], "action_text": "a"}]}'
    monkeypatch.setattr(sarvam_client, 'chat', fake_chat(bad)[0])
    assert llm.structure('x').red_flags == []


def test_retry_once_with_error_then_success(monkeypatch):
    chat, calls = fake_chat('not json', GOOD)
    monkeypatch.setattr(sarvam_client, 'chat', chat)
    assert llm.structure('x').vitals.bp == '150/95'
    assert len(calls) == 2 and 'previous output was invalid' in calls[1]


def test_wrong_types_trigger_retry(monkeypatch):
    chat, calls = fake_chat('{"vitals": "150/95"}', GOOD)
    monkeypatch.setattr(sarvam_client, 'chat', chat)
    assert llm.structure('x').vitals.bp == '150/95' and len(calls) == 2


def test_two_failures_return_empty_record_with_warning(monkeypatch):
    monkeypatch.setattr(sarvam_client, 'chat', fake_chat('nope', 'still nope')[0])
    r = llm.structure('x')
    assert r.prescription == [] and r.warnings


def test_prompt_examples_hold_out_s3_and_require_english_output():
    p = llm.system_prompt()
    assert p.count('Example transcript:') == 3 and 'Metformin' not in p and 'must be in English' in p
    d = llm.DEVANAGARI_EXAMPLE
    assert all(q in d['transcript'] for q in d['evidence'].values())


@pytest.mark.parametrize('given,expected', [
    ('metoprolol', 'Metoprolol'), ('Amlodipin', 'Amlodipine'), ('Metaformin', 'Metformin'),
    ('Zzzdrug', 'Zzzdrug'), ('', '')])
def test_formulary_normalize(given, expected):
    assert formulary.normalize(given) == expected


def test_formulary_size():
    assert 35 <= len(formulary.DRUGS) <= 50
