import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import main
import mock_data
import sarvam_client


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_STREAMING', True)
    return TestClient(main.app)


def run_stream(client, chunks, url='/api/stream?language=mr-IN&scenario=S1'):
    out = []
    with client.websocket_connect(url) as ws:
        for _ in range(chunks):
            ws.send_bytes(b'RIFF-chunk')
            out.append(ws.receive_json())
        ws.send_text('end')
        out.append(ws.receive_json())
    return out


def test_mock_stream_emits_partial_text_per_chunk_then_done(client, monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', True)
    words = mock_data.SCENARIOS['S1']['transcript'].split()
    msgs = run_stream(client, 3)
    assert [m['type'] for m in msgs] == ['partial', 'partial', 'partial', 'done']
    assert msgs[0]['text'] == ' '.join(words[:4]) and msgs[-1]['transcript'] == ' '.join(words[:12])


def test_stream_off_message(monkeypatch):
    monkeypatch.setattr(config, 'ENABLE_STREAMING', False)
    with TestClient(main.app).websocket_connect('/api/stream') as ws:
        msg = ws.receive_json()
    assert msg['type'] == 'error' and 'ENABLE_STREAMING' in msg['error']


def test_real_relay_gets_chunks_and_final_transcript_joins_segments(client, monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)
    received = []

    async def fake_relay(next_audio, emit, language, **kw):
        assert language == 'hi-IN'
        while (c := await next_audio()) is not None:
            received.append(c)
            await emit(f'seg{len(received)}')

    monkeypatch.setattr(sarvam_client, 'stream_relay', fake_relay)
    msgs = run_stream(client, 2, '/api/stream?language=hi-IN')
    assert received == [b'RIFF-chunk'] * 2
    assert msgs[-1] == {'type': 'done', 'transcript': 'seg1 seg2'}


def test_sarvam_failure_during_stream_is_reported(client, monkeypatch):
    monkeypatch.setattr(config, 'MOCK_MODE', False)

    async def failing(next_audio, emit, language, **kw):
        raise sarvam_client.SarvamError('Sarvam rate limit hit.')

    monkeypatch.setattr(sarvam_client, 'stream_relay', failing)
    with client.websocket_connect('/api/stream') as ws:
        ws.send_bytes(b'x')
        assert ws.receive_json() == {'type': 'error', 'error': 'Sarvam rate limit hit.'}
