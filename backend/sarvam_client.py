"""The ONLY file that imports sarvamai. All wrappers are no-network in MOCK_MODE."""
import asyncio
import base64
import json
import tempfile
import time
from pathlib import Path

import config

MOCK_WAV = Path(__file__).resolve().parent.parent / 'demo' / 'audio' / 'mock.wav'

_client = None


class SarvamError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


_STATUS_MESSAGES = {
    400: 'Bad request sent to Sarvam.',
    402: 'Sarvam credits exhausted.',
    403: 'Sarvam rejected the API key.',
    422: 'Invalid parameters sent to Sarvam.',
    429: 'Sarvam rate limit hit.',
}


def _get_client():
    global _client
    if _client is None:
        if not config.SARVAM_API_KEY:
            raise SarvamError('SARVAM_API_KEY is not set in .env.', 500)
        from sarvamai import SarvamAI
        _client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    return _client


def _call(fn):
    """Run fn(); retry once on 429 or timeout with backoff; map ApiError to SarvamError."""
    import httpx
    from sarvamai.core.api_error import ApiError
    for attempt in range(2):
        try:
            return fn()
        except httpx.TimeoutException:
            if attempt == 0:
                time.sleep(2)
                continue
            raise SarvamError('Sarvam did not respond in time.', 502)
        except ApiError as e:
            if e.status_code == 429 and attempt == 0:
                time.sleep(2)
                continue
            msg = _STATUS_MESSAGES.get(e.status_code, f'Sarvam API error {e.status_code}.')
            raise SarvamError(msg, 502)


_DEFAULT = object()


def chat(model, system, user, temperature=None, max_tokens=None, reasoning_effort=_DEFAULT):
    """reasoning_effort: 'low'/'medium'/'high', or None to switch thinking off (docs.sarvam.ai chat completions)."""
    if config.MOCK_MODE:
        return '{}'
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': user})
    extra = {k: v for k, v in (('temperature', temperature), ('max_tokens', max_tokens)) if v is not None}
    if reasoning_effort is not _DEFAULT:
        extra['reasoning_effort'] = reasoning_effort
    r = _call(lambda: _get_client().chat.completions(model=model, messages=messages, **extra))
    return r.choices[0].message.content


def stt(path, model=None, mode=None, language_code='unknown', keyterms=None):
    """Returns {'transcript', 'language'}. language_code='unknown' means auto-detect. keyterms (saaras:v4 only,
    max 50 terms of 64 chars) bias recognition towards those words."""
    if config.MOCK_MODE:
        return {'transcript': '', 'language': ''}
    model, mode = model or config.STT_MODEL, mode or config.STT_MODE
    extra = {'keyterms': keyterms} if keyterms else {}

    def run():
        with open(path, 'rb') as f:
            return _get_client().speech_to_text.transcribe(
                file=f, model=model, mode=mode, language_code=language_code, **extra)
    r = _call(run)
    return {'transcript': r.transcript or '', 'language': r.language_code or ''}


def tts(text, language_code, speaker=None, model=None, **options):
    """Returns WAV bytes. options (e.g. pace=1.3) are passed to the SDK."""
    if config.MOCK_MODE:
        return MOCK_WAV.read_bytes()
    speaker = speaker or config.TTS_SPEAKERS.get(language_code, '')
    if not speaker:
        raise SarvamError(f'No TTS speaker configured for {language_code} (set TTS_SPEAKER_* in .env).', 500)
    model = model or config.TTS_MODEL
    r = _call(lambda: _get_client().text_to_speech.convert(
        language_code=language_code, text=text, model=model, speaker=speaker, **options))
    return base64.b64decode(''.join(r.audios))


def stt_diarized(path, language_code='unknown', num_speakers=None, keyterms=None, timeout=300):
    """Batch API job with speaker diarization (REST has no diarization). Returns
    {'transcript', 'language', 'entries': [{'speaker_id', 'transcript', 'start_time_seconds', 'end_time_seconds'}]}."""
    if config.MOCK_MODE:
        return {'transcript': '', 'language': '', 'entries': []}

    def run():
        kw = {'model': config.STT_MODEL, 'mode': config.STT_MODE, 'language_code': language_code, 'with_diarization': True}
        if num_speakers:
            kw['num_speakers'] = num_speakers
        if keyterms:
            kw['keyterms'] = keyterms
        job = _get_client().speech_to_text_job.create_job(**kw)
        job.upload_files(file_paths=[str(path)])
        job.start()
        job.wait_until_complete(timeout=timeout)
        results = job.get_file_results()
        if results['failed']:
            raise SarvamError('Sarvam could not process the audio for speaker separation.', 502)
        with tempfile.TemporaryDirectory(prefix='vs_batch_') as out:
            job.download_outputs(output_dir=out)
            files = sorted(Path(out).glob('*.json'))
            if not files:
                raise SarvamError('Sarvam returned no transcript for the audio.', 502)
            return json.loads(files[0].read_text(encoding='utf-8'))
    try:
        data = _call(run)
    except TimeoutError:
        raise SarvamError('Speaker separation timed out.', 502)
    entries = (data.get('diarized_transcript') or {}).get('entries') or []
    return {'transcript': data.get('transcript') or '', 'language': data.get('language_code') or '', 'entries': entries}


# ---- Document AI (prescription photos). The job is async: start, poll status, fetch results.
def doc_extract_start(filename, data, mime, schema):
    if config.MOCK_MODE:
        return 'mock-job'
    return _call(lambda: _get_client().doc_ai.extract(file=[(filename, data, mime)], schema=schema, output_format='json')).job_id


def doc_status(job_id):
    """Lower-case job status: 'pending', 'completed', 'failed', ..."""
    return str(_call(lambda: _get_client().doc_ai.get_status(job_id)).status).lower()


def doc_results(job_id):
    r = _call(lambda: _get_client().doc_ai.get_results(job_id))
    return {'result': r.result or {}, 'annotations': r.annotations or {}}


# ---- Real-time streaming STT (WebSocket). WAV chunks in, transcript segments out.
async def stream_relay(next_audio, emit, language_code, flush_wait_s=8, flush_every=2):
    """next_audio(): awaitable returning a WAV chunk (bytes) or None when the speaker stops.
    emit(text): awaitable called for every transcript segment Sarvam returns."""
    from sarvamai import AsyncSarvamAI
    from sarvamai.core.api_error import ApiError
    if not config.SARVAM_API_KEY:
        raise SarvamError('SARVAM_API_KEY is not set in .env.', 500)
    client = AsyncSarvamAI(api_subscription_key=config.SARVAM_API_KEY)
    try:
        async with client.speech_to_text_streaming.connect(
                model=config.STT_MODEL, mode=config.STT_MODE, language_code=language_code,
                sample_rate=16000, flush_signal=True, high_vad_sensitivity=True) as ws:
            async def pump_in():
                sent = 0
                while (chunk := await next_audio()) is not None:
                    await ws.transcribe(audio=base64.b64encode(chunk).decode(), encoding='audio/wav', sample_rate=16000)
                    sent += 1
                    if sent % flush_every == 0:
                        await ws.flush()   # do not wait for a pause in speech: ask for text every few chunks
                await ws.flush()

            async def pump_out():
                async for msg in ws:
                    if msg.type == 'data' and getattr(msg.data, 'transcript', ''):
                        await emit(msg.data.transcript)

            reader = asyncio.create_task(pump_out())
            try:
                await pump_in()
                await asyncio.wait_for(asyncio.shield(reader), timeout=flush_wait_s)   # trailing segments
            except asyncio.TimeoutError:
                pass
            finally:
                reader.cancel()
    except ApiError as e:
        raise SarvamError(_STATUS_MESSAGES.get(e.status_code, f'Sarvam streaming error {e.status_code}.'), 502)
