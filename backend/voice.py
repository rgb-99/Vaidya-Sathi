"""Speech-to-text pipeline. Audio lives only in a temp dir that is deleted before returning."""
import io
import re
import subprocess
import wave
import tempfile
from collections import Counter
from pathlib import Path

import config
import mock_data
import sarvam_client

# Formats the Sarvam REST endpoint accepts (docs.sarvam.ai, STT overview). PCM is excluded: it needs a codec hint.
ACCEPTED_EXT = {'.wav', '.mp3', '.aac', '.aiff', '.aif', '.ogg', '.opus', '.flac',
                '.mp4', '.m4a', '.amr', '.wma', '.webm'}
REST_MAX_S = 30.0       # Sarvam REST limit per request
CHUNK_MAX_S = 28.0      # stay under the limit with a safety margin
MIN_SPLIT_S = 10.0      # never cut a chunk shorter than this when a silence is available


class AudioError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class AudioTooLongError(AudioError):
    def __init__(self, message):
        super().__init__(message, 413)


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise AudioError('ffmpeg is not installed on the server.', 500)


def probe_duration(path):
    """Seconds, or None when the container has no duration (common for browser WebM)."""
    r = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'default=noprint_wrappers=1:nokey=1', str(path)])
    if r.returncode != 0:
        raise AudioError('The uploaded file is not valid audio.')
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def to_wav(src, dst):
    """Decode anything ffmpeg understands to 16 kHz mono WAV (Sarvam's recommended input)."""
    r = _run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-ac', '1', '-ar', '16000', str(dst)])
    if r.returncode != 0:
        raise AudioError('The uploaded file is not valid audio.')


def find_silences(path):
    """Midpoints (seconds) of silent gaps, used as preferred cut points."""
    r = _run(['ffmpeg', '-v', 'info', '-i', str(path), '-af', 'silencedetect=noise=-35dB:d=0.3',
              '-f', 'null', '-'])
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return [(s + e) / 2 for s, e in zip(starts, ends)]


def plan_chunks(duration, silences, max_s=CHUNK_MAX_S):
    """Split [0, duration] into (start, end) windows of at most max_s, cutting at silences when possible."""
    chunks, start = [], 0.0
    while duration - start > max_s:
        limit = start + max_s
        cuts = [s for s in silences if start + MIN_SPLIT_S <= s <= limit]
        cut = max(cuts) if cuts else limit
        chunks.append((start, cut))
        start = cut
    chunks.append((start, duration))
    return chunks


def _cut(wav, start, end, dst):
    r = _run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{start:.3f}', '-t', f'{end - start:.3f}',
              '-i', str(wav), '-c', 'copy', str(dst)])
    if r.returncode != 0:
        raise AudioError('Could not split the audio.', 500)


def _mock(filename):
    s = mock_data.SCENARIOS[mock_data.scenario_for_filename(filename)]
    return {'transcript': s['transcript'], 'language': s['language']}


def transcribe(audio_bytes, filename):
    """Returns {'transcript', 'language'}. Raises AudioError (400/413) or SarvamError (502)."""
    if config.MOCK_MODE:
        return _mock(filename)
    if not audio_bytes:
        raise AudioError('No audio received.')

    ext = Path(filename or '').suffix.lower()
    with tempfile.TemporaryDirectory(prefix='vs_audio_') as tmp:
        tmp = Path(tmp)
        src = tmp / f'upload{ext if ext in ACCEPTED_EXT else ".bin"}'
        src.write_bytes(audio_bytes)

        duration = probe_duration(src)
        if duration is not None and duration > config.MAX_AUDIO_SECONDS:
            raise AudioTooLongError(f'Audio is longer than {config.MAX_AUDIO_SECONDS} seconds.')
        if ext in ACCEPTED_EXT and duration is not None and duration <= REST_MAX_S:
            return sarvam_client.stt(src)

        # Unknown duration (browser WebM), unaccepted format, or longer than one request allows.
        wav = tmp / 'audio.wav'
        to_wav(src, wav)
        duration = probe_duration(wav)
        if duration > config.MAX_AUDIO_SECONDS:
            raise AudioTooLongError(f'Audio is longer than {config.MAX_AUDIO_SECONDS} seconds.')
        if duration <= REST_MAX_S:
            return sarvam_client.stt(wav)

        results = []
        for i, (a, b) in enumerate(plan_chunks(duration, find_silences(wav))):
            part = tmp / f'part{i}.wav'
            _cut(wav, a, b, part)
            results.append(sarvam_client.stt(part))
        langs = [r['language'] for r in results if r['language']]
        return {
            'transcript': ' '.join(r['transcript'].strip() for r in results if r['transcript'].strip()),
            'language': Counter(langs).most_common(1)[0][0] if langs else '',
        }


TTS_MAX_CHARS = 2000  # Bulbul REST limit is 2,500 characters per request; keep a margin


def split_sentences(text, max_chars=TTS_MAX_CHARS):
    """Split on sentence boundaries into pieces of at most max_chars (hard-split only if a sentence is longer)."""
    sentences = [s.strip() for s in re.findall(r'[^.?!।\n]+[.?!।]?', text) if s.strip()]
    pieces, cur = [], ''
    for s in sentences:
        while len(s) > max_chars:
            if cur:
                pieces.append(cur)
                cur = ''
            pieces.append(s[:max_chars])
            s = s[max_chars:]
        if cur and len(cur) + 1 + len(s) > max_chars:
            pieces.append(cur)
            cur = ''
        cur = f'{cur} {s}'.strip()
    if cur:
        pieces.append(cur)
    return pieces


def join_wavs(wavs):
    if len(wavs) == 1:
        return wavs[0]
    out, params = io.BytesIO(), None
    with wave.open(out, 'wb') as w:
        for data in wavs:
            with wave.open(io.BytesIO(data)) as r:
                if params is None:
                    params = r.getparams()
                    w.setparams(params)
                w.writeframes(r.readframes(r.getnframes()))
    return out.getvalue()


def speak(text, language):
    """Text -> WAV bytes in the configured voice for the language. Mock mode returns the bundled WAV."""
    if config.MOCK_MODE:
        return sarvam_client.tts(text, language)
    return join_wavs([sarvam_client.tts(p, language) for p in split_sentences(text)])
