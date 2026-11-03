"""The ONLY file that imports sarvamai. All wrappers are no-network in MOCK_MODE."""
import base64
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


def stt(path, model=None, mode=None, language_code='unknown'):
    """Returns {'transcript', 'language'}. language_code='unknown' means auto-detect."""
    if config.MOCK_MODE:
        return {'transcript': '', 'language': ''}
    model, mode = model or config.STT_MODEL, mode or config.STT_MODE

    def run():
        with open(path, 'rb') as f:
            return _get_client().speech_to_text.transcribe(
                file=f, model=model, mode=mode, language_code=language_code)
    r = _call(run)
    return {'transcript': r.transcript or '', 'language': r.language_code or ''}


def tts(text, language_code, speaker=None, model=None):
    """Returns WAV bytes."""
    if config.MOCK_MODE:
        return MOCK_WAV.read_bytes()
    speaker = speaker or config.TTS_SPEAKERS.get(language_code, '')
    if not speaker:
        raise SarvamError(f'No TTS speaker configured for {language_code} (set TTS_SPEAKER_* in .env).', 500)
    model = model or config.TTS_MODEL
    r = _call(lambda: _get_client().text_to_speech.convert(
        language_code=language_code, text=text, model=model, speaker=speaker))
    return base64.b64decode(''.join(r.audios))
