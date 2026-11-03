import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import sarvam_client
import voice

needs_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg not installed')


def make_wav(path, segments, rate=8000):
    """segments: list of (seconds, loud). Loud = 440 Hz tone, quiet = digital silence."""
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for secs, loud in segments:
            n = int(secs * rate)
            w.writeframes(b''.join(
                struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / rate)) if loud else 0)
                for i in range(n)))
    return path


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)
    monkeypatch.setattr(config, 'MAX_AUDIO_SECONDS', 180)


# ---------- chunking logic (pure) ----------

def test_short_audio_is_one_chunk():
    assert voice.plan_chunks(12.0, []) == [(0.0, 12.0)]


def test_chunks_cover_audio_contiguously_and_respect_limit():
    chunks = voice.plan_chunks(95.0, [])
    assert chunks[0][0] == 0.0 and chunks[-1][1] == 95.0
    for (_, end), (start, _) in zip(chunks, chunks[1:]):
        assert end == start
    assert all(b - a <= voice.CHUNK_MAX_S for a, b in chunks)


def test_chunks_prefer_the_latest_silence_in_window():
    chunks = voice.plan_chunks(50.0, [15.0, 26.5, 40.0])
    assert chunks[0] == (0.0, 26.5)
    assert chunks[1] == (26.5, 50.0)


def test_silence_too_early_is_ignored():
    # A silence at 2 s would make a tiny first chunk; fall back to a hard cut.
    chunks = voice.plan_chunks(40.0, [2.0])
    assert chunks[0] == (0.0, voice.CHUNK_MAX_S)


# ---------- ffmpeg conversion ----------

@needs_ffmpeg
def test_webm_converts_to_16k_mono_wav(tmp_path):
    src = make_wav(tmp_path / 'in.wav', [(2, True)], rate=44100)
    webm = tmp_path / 'in.webm'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), str(webm)], check=True)
    out = tmp_path / 'out.wav'
    voice.to_wav(webm, out)
    with wave.open(str(out)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
    assert 1.8 < voice.probe_duration(out) < 2.3


@needs_ffmpeg
def test_garbage_is_rejected_as_bad_file():
    with pytest.raises(voice.AudioError) as e:
        voice.transcribe(b'this is not audio at all', 'clip.wav')
    assert e.value.status_code == 400


def test_empty_upload_is_rejected():
    with pytest.raises(voice.AudioError) as e:
        voice.transcribe(b'', 'clip.wav')
    assert e.value.status_code == 400


@needs_ffmpeg
def test_too_long_audio_is_413(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'MAX_AUDIO_SECONDS', 5)
    wav = make_wav(tmp_path / 'long.wav', [(8, True)])
    with pytest.raises(voice.AudioTooLongError) as e:
        voice.transcribe(wav.read_bytes(), 'long.wav')
    assert e.value.status_code == 413


# ---------- full pipeline with the Sarvam call mocked ----------

@needs_ffmpeg
def test_short_wav_goes_straight_to_sarvam(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sarvam_client, 'stt', lambda p: calls.append(Path(p)) or
                        {'transcript': 'hello', 'language': 'hi-IN'})
    wav = make_wav(tmp_path / 'a.wav', [(3, True)])
    assert voice.transcribe(wav.read_bytes(), 'a.wav') == {'transcript': 'hello', 'language': 'hi-IN'}
    assert len(calls) == 1
    assert not calls[0].exists(), 'temp audio must be deleted afterwards'


@needs_ffmpeg
def test_long_audio_is_chunked_cut_at_silence_and_joined(tmp_path, monkeypatch):
    sent = []

    def fake_stt(path):
        sent.append(voice.probe_duration(path))
        return {'transcript': f'part{len(sent)}', 'language': 'mr-IN'}

    monkeypatch.setattr(sarvam_client, 'stt', fake_stt)
    # tone 20 s, gap 2 s, tone 28 s, gap 2 s, tone 13 s = 65 s
    wav = make_wav(tmp_path / 'long.wav', [(20, True), (2, False), (28, True), (2, False), (13, True)])
    out = voice.transcribe(wav.read_bytes(), 'long.wav')
    assert len(sent) >= 3
    assert all(d <= voice.REST_MAX_S for d in sent)
    assert abs(sum(sent) - 65) < 1.0
    assert out['transcript'] == ' '.join(f'part{i + 1}' for i in range(len(sent)))
    assert out['language'] == 'mr-IN'


def test_mock_mode_returns_canned_transcript_without_sarvam(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    monkeypatch.setattr(sarvam_client, 'stt', lambda *a, **k: pytest.fail('network call in mock mode'))
    out = voice.transcribe(b'x', 'S2.webm')
    assert 'BP 90/60' in out['transcript']
    assert voice.transcribe(b'x', 'whatever.webm')['language'] == 'mr-IN'


# ---------- Sarvam error mapping ----------

def api_error(status):
    from sarvamai.core.api_error import ApiError
    return ApiError(status_code=status, body={})


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(sarvam_client.time, 'sleep', lambda s: None)


@pytest.mark.parametrize('status,fragment', [
    (400, 'Bad request'), (402, 'credits'), (403, 'API key'), (422, 'Invalid parameters'), (500, 'error 500')])
def test_api_errors_map_to_friendly_502(status, fragment, no_sleep):
    def boom():
        raise api_error(status)
    with pytest.raises(sarvam_client.SarvamError) as e:
        sarvam_client._call(boom)
    assert fragment in str(e.value) and e.value.status_code == 502


def test_429_is_retried_once_then_succeeds(no_sleep):
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise api_error(429)
        return 'ok'
    assert sarvam_client._call(flaky) == 'ok' and len(attempts) == 2


def test_429_twice_surfaces_rate_limit_error(no_sleep):
    attempts = []

    def always():
        attempts.append(1)
        raise api_error(429)
    with pytest.raises(sarvam_client.SarvamError, match='rate limit'):
        sarvam_client._call(always)
    assert len(attempts) == 2


def test_timeout_is_retried_once_then_friendly_error(no_sleep):
    import httpx
    attempts = []

    def slow():
        attempts.append(1)
        raise httpx.ReadTimeout('slow')
    with pytest.raises(sarvam_client.SarvamError, match='in time'):
        sarvam_client._call(slow)
    assert len(attempts) == 2


def test_stt_maps_response_fields(monkeypatch, tmp_path):
    class R:
        transcript = 'namaste'
        language_code = None

    class Client:
        class speech_to_text:
            @staticmethod
            def transcribe(**kw):
                assert kw['language_code'] == 'unknown' and kw['model'] == config.STT_MODEL
                return R()

    monkeypatch.setattr(config, 'MOCK_MODE', False)
    monkeypatch.setattr(sarvam_client, '_get_client', lambda: Client)
    f = tmp_path / 'a.wav'
    f.write_bytes(b'x')
    assert sarvam_client.stt(f) == {'transcript': 'namaste', 'language': ''}
