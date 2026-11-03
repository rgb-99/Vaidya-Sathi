import asyncio
import io
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
import main
import voice


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'app.db')


def upload(name='a.wav'):
    return UploadFile(io.BytesIO(b'audio-bytes'), filename=name)


def sync(client_id, name='a.wav'):
    return asyncio.run(main.sync(client_id=client_id, audio=upload(name)))


def test_same_client_id_never_transcribes_twice(monkeypatch):
    calls = []
    monkeypatch.setattr(voice, 'transcribe', lambda data, name: calls.append(name) or {'transcript': 'hello', 'language': 'mr-IN', 'utterances': []})
    first = sync('abc12345-1')
    again = sync('abc12345-1')
    retry_with_other_file = sync('abc12345-1', 'other.wav')
    assert len(calls) == 1
    assert first['duplicate'] is False and again['duplicate'] is True and retry_with_other_file['transcript'] == 'hello'


def test_different_ids_are_independent(monkeypatch):
    n = []
    monkeypatch.setattr(voice, 'transcribe', lambda data, name: n.append(1) or {'transcript': f't{len(n)}', 'language': '', 'utterances': []})
    assert [sync('aaaaaaaa-1')['transcript'], sync('bbbbbbbb-2')['transcript']] == ['t1', 't2']


def test_result_survives_in_the_database_and_has_no_audio(monkeypatch):
    monkeypatch.setattr(voice, 'transcribe', lambda data, name: {'transcript': 'x', 'language': 'hi-IN', 'utterances': []})
    sync('abc12345-2')
    stored = db.get_sync('abc12345-2')
    assert stored == {'transcript': 'x', 'language': 'hi-IN', 'utterances': []}


@pytest.mark.parametrize('bad', ['', 'short', 'has space in it!', '../../etc/passwd', 'x' * 65])
def test_invalid_client_ids_are_rejected(bad):
    with pytest.raises(HTTPException) as e:
        sync(bad)
    assert e.value.status_code == 400


def test_failed_transcription_is_not_cached_so_a_retry_can_succeed(monkeypatch):
    attempts = []

    def flaky(data, name):
        attempts.append(1)
        if len(attempts) == 1:
            raise voice.AudioError('The uploaded file is not valid audio.')
        return {'transcript': 'ok', 'language': '', 'utterances': []}

    monkeypatch.setattr(voice, 'transcribe', flaky)
    with pytest.raises(voice.AudioError):
        sync('abc12345-3')
    assert sync('abc12345-3')['transcript'] == 'ok' and len(attempts) == 2


def test_mock_mode_sync_works_offline_of_sarvam(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    assert 'BP check kela' in sync('abc12345-4', 'S1.webm')['transcript']
