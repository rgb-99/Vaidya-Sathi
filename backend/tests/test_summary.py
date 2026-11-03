import io
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import llm
import mock_data
import sarvam_client
import voice

GOOD = 'Your blood pressure is high. Morning: one Metoprolol 50mg tablet. Night: one Amlodipine 5mg tablet. Eat less salt. If you feel worse, go to the hospital immediately.'


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)


@pytest.fixture
def s1():
    return mock_data.scenario_record('S1')


def test_post_check_accepts_faithful_summary(s1):
    assert llm.check_summary(GOOD, s1) == []


@pytest.mark.parametrize('text,fragment', [
    (GOOD + ' Also take Paracetamol.', 'not prescribed: Paracetamol'),
    (GOOD.replace('50mg', '100mg'), 'dose not prescribed: 100mg'),
    (GOOD.replace('Amlodipine 5mg', 'Amlodipine'), 'dose missing: 5mg'),
    (GOOD.replace('Metoprolol', 'the pill'), 'drug missing: Metoprolol'),
    (GOOD + ' Take OD.', 'abbreviation'),
    (GOOD + ' word' * 120, 'over 120'),
])
def test_post_check_rejects(text, fragment, s1):
    assert any(fragment in p for p in llm.check_summary(text, s1))


def test_added_drug_is_regenerated_then_template_used(monkeypatch, s1):
    calls = []
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: calls.append(1) or GOOD + ' Also take Aspirin.')
    text, fallback = llm.summarize(s1, 'en-IN')
    assert fallback and len(calls) == 2
    assert 'Aspirin' not in text and 'Metoprolol' in text and '50mg' in text


def test_good_summary_used_without_fallback(monkeypatch, s1):
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: GOOD)
    assert llm.summarize(s1, 'en-IN') == (GOOD, False)


def test_second_attempt_can_succeed(monkeypatch, s1):
    outs = iter([GOOD + ' Take Aspirin.', GOOD])
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: next(outs))
    assert llm.summarize(s1, 'en-IN') == (GOOD, False)


@pytest.mark.parametrize('lang', ['mr-IN', 'hi-IN', 'en-IN'])
@pytest.mark.parametrize('sid', ['S1', 'S2', 'S3'])
def test_template_fallback_each_language(lang, sid):
    rec = mock_data.scenario_record(sid)
    text = llm.template_summary(rec, lang)
    assert llm.PHRASES[lang]['worse'] in text
    for rx in rec.prescription:
        assert rx.drug in text and rx.dose in text
    assert len(text.split()) <= 120


def test_template_english_passes_post_check():
    for sid in ('S1', 'S3'):
        rec = mock_data.scenario_record(sid)
        assert llm.check_summary(llm.template_summary(rec, 'en-IN'), rec) == []


def test_template_with_no_medicines():
    assert llm.PHRASES['hi-IN']['none'] in llm.template_summary(mock_data.scenario_record('S2'), 'hi-IN')


def wav(frames):
    b = io.BytesIO()
    with wave.open(b, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b'\x01\x00' * frames)
    return b.getvalue()


def test_split_respects_limit_and_sentence_boundaries():
    text = ' '.join(f'Sentence number {i} is here.' for i in range(300))
    pieces = voice.split_sentences(text, max_chars=500)
    assert all(len(p) <= 500 for p in pieces) and len(pieces) > 1
    assert all(p.endswith('.') for p in pieces)
    assert ' '.join(pieces) == text


def test_split_handles_danda_and_overlong_sentence():
    assert voice.split_sentences('एक। दो। तीन।') == ['एक। दो। तीन।']
    assert [len(p) for p in voice.split_sentences('x' * 25, max_chars=10)] == [10, 10, 5]


def test_speak_splits_and_concatenates(monkeypatch):
    monkeypatch.setattr(voice, 'split_sentences', lambda t: ['a.', 'b.', 'c.'])
    monkeypatch.setattr(sarvam_client, 'tts', lambda text, lang, **k: wav(100))
    out = voice.speak('a. b. c.', 'mr-IN')
    with wave.open(io.BytesIO(out)) as r:
        assert r.getnframes() == 300


def test_speak_mock_returns_bundled_wav(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    assert voice.speak('x', 'mr-IN')[:4] == b'RIFF'


def test_english_closer_is_replaced_for_indic_languages(monkeypatch, s1):
    marathi = 'सकाळी Metoprolol 50mg एक गोळी. रात्री Amlodipine 5mg एक गोळी.\n\nif you feel worse, go to the hospital immediately.'
    monkeypatch.setattr(sarvam_client, 'chat', lambda *a, **k: marathi)
    text, fb = llm.summarize(s1, 'mr-IN')
    assert not fb and text.endswith(llm.PHRASES['mr-IN']['worse']) and 'if you feel' not in text and '\n' not in text
