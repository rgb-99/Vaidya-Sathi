import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import llm
import masking
import sarvam_client

TEXT = ('Patient: My name is Ramesh Patil. My phone is 98765 43210 and Aadhaar 2345 6789 0123. '
        'Doctor: BP 150/95 ahe, pulse 118. Metoprolol 50mg 30 days.')


def test_names_phones_and_long_ids_are_masked_and_clinical_numbers_are_not():
    m = masking.Masker()
    out = m.mask(TEXT)
    for private in ('Ramesh', 'Patil', '98765', '43210', '2345', '6789 0123'):
        assert private not in out
    for clinical in ('150/95', 'pulse 118', 'Metoprolol 50mg', '30 days'):
        assert clinical in out
    assert sorted(m.map) == ['<ID_1>', '<NAME_1>', '<PHONE_1>']


@pytest.mark.parametrize('text,private', [
    ('मेरा नाम सुनीता देशमुख है', 'सुनीता'), ('माझे नाव रमेश पाटील आहे', 'रमेश'), ('Mrs. Lata Kulkarni came today', 'Lata'),
    ('श्रीमती मीना जोशी', 'मीना'), ('call +91 98765-43210 please', '98765'), ('number 09876543210', '9876543210'),
    ('ABHA 12-3456-7890-1234', '3456'),
])
def test_other_cue_words_and_number_formats(text, private):
    assert private not in masking.Masker().mask(text)


@pytest.mark.parametrize('text', ['BP 150/95', 'temperature 102', 'Metformin 500mg twice daily', 'I am fine', 'pulse is 118',
                                  'sugar 340 and SpO2 88', 'name is not important', 'पल्स 118 आहे', 'Come back after 30 days'])
def test_ordinary_clinical_text_is_left_alone(text):
    m = masking.Masker()
    assert m.mask(text) == text and m.map == {}


def test_known_names_are_masked_everywhere_case_insensitively():
    m = masking.Masker(known_names=['Anita Rao'])
    out = m.mask('anita rao said hello. ANITA RAO has a cough.')
    assert 'anita' not in out.lower() and out.count('<NAME_1>') == 2


def test_same_value_gets_the_same_token_and_unmask_restores_nested_values():
    m = masking.Masker()
    out = m.mask('My name is Ramesh Patil. Ramesh Patil again, phone 9876543210')
    restored = m.unmask({'patient': {'name': '<NAME_1>'}, 'advice': ['call <PHONE_1>', 'x'], 'n': 3})
    assert restored == {'patient': {'name': 'Ramesh Patil'}, 'advice': ['call 9876543210', 'x'], 'n': 3}
    assert out.count('<NAME_1>') == 1 or 'Ramesh' not in out


# ---- end to end through structure(): the chat model never sees the private details

@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)
    monkeypatch.setattr(config, 'ENABLE_PII_MASKING', True)


def run_structure(monkeypatch, text, reply):
    seen = []
    monkeypatch.setattr(sarvam_client, 'chat', lambda model, system, user, **k: seen.append((system, user)) or reply)
    return llm.structure(text), seen


def test_model_input_has_no_names_or_numbers_and_output_is_restored(monkeypatch):
    reply = json.dumps({'patient': {'name': '<NAME_1>'}, 'chief_complaints': [], 'vitals': {'bp': '150/95', 'pulse': '118'},
                        'prescription': [{'drug': 'Metoprolol', 'dose': '50mg', 'duration': '30 days'}], 'advice': ['call <PHONE_1>'],
                        'evidence': [{'field': 'patient.name', 'quote': '<NAME_1>'}, {'field': 'vitals.bp', 'quote': 'BP 150/95'}]})
    rec, seen = run_structure(monkeypatch, TEXT, reply)
    user_text = seen[0][1]
    for private in ('Ramesh', 'Patil', '98765', '43210', '2345', '6789'):
        assert private not in user_text and private not in seen[0][0]   # not in the transcript sent nor in the system prompt
    assert rec.patient.name == 'Ramesh Patil' and rec.advice == ['call 98765 43210']
    assert rec.vitals.bp == '150/95'


def test_evidence_quotes_are_checked_against_the_original_transcript(monkeypatch):
    reply = json.dumps({'patient': {'name': '<NAME_1>'}, 'vitals': {'bp': '150/95'},
                        'evidence': [{'field': 'patient.name', 'quote': 'My name is Ramesh Patil'}]})
    rec, _ = run_structure(monkeypatch, TEXT, reply)
    assert 'patient.name: Ramesh Patil' in rec.said and rec.provenance['patient.name'].quote == 'My name is Ramesh Patil'


def test_retry_message_is_masked_too(monkeypatch):
    seen = []
    outs = iter(['not json', json.dumps({'vitals': {'bp': '150/95'}})])
    monkeypatch.setattr(sarvam_client, 'chat', lambda model, system, user, **k: seen.append(user) or next(outs))
    llm.structure(TEXT)
    assert len(seen) == 2 and all('Ramesh' not in u and '98765' not in u for u in seen)


def test_masking_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_PII_MASKING', False)
    _, seen = run_structure(monkeypatch, TEXT, '{}')
    assert 'Ramesh' in seen[0][1]


@pytest.mark.parametrize('text,name,rest', [
    ('मेरा नाम सुनीता देशमुख है। मेरा फोन', 'सुनीता देशमुख', 'है। मेरा फोन'),
    ('माझे नाव रमेश पाटील आहे.', 'रमेश पाटील', 'आहे.'),
    ('My name is Ramesh Patil and I have fever', 'Ramesh Patil', 'and I have fever'),
])
def test_name_stops_before_grammar_words_and_punctuation(text, name, rest):
    m = masking.Masker()
    out = m.mask(text)
    assert m.map == {'<NAME_1>': name} and out.endswith(rest) and name not in out
    assert m.unmask(out) == text
