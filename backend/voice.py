"""Speech-to-text pipeline. Audio lives only in a temp dir that is deleted before returning."""
import io
import re
import subprocess
import wave
import tempfile
from collections import Counter
from pathlib import Path

import config
import formulary
import mock_data
import sarvam_client
from schemas import Utterance

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


ROLE_LABELS = {'doctor': 'clinician', 'nurse': 'clinician', 'patient': 'patient'}
INSTRUCTION_RE = re.compile(r'\d\s*(?:mg|mcg|ml)\b|\b(?:tablet|take|daily|days?|divas|ghet|kara)\b|गोळी|गोली|घ्या|लें|लेना|लीजिए', re.I)


def _stt(path):
    """One REST call; passes the formulary as key terms when ENABLE_KEYTERMS=true (saaras:v4)."""
    kw = {'keyterms': formulary.key_terms()} if config.ENABLE_KEYTERMS else {}
    return sarvam_client.stt(path, **kw)


def role_score(text):
    """How much a turn sounds like a clinician: drug names count triple, plus doses and instructions."""
    drugs = sum(bool(re.search(rf'\b{re.escape(d.lower())}\b', text.lower())) for d in formulary.DRUGS)
    return 3 * drugs + len(INSTRUCTION_RE.findall(text))


def assign_roles(entries):
    """Diarized entries -> Utterances. The speaker who states drugs, doses or instructions is the clinician.
    One speaker, or no clear winner: every turn stays 'unknown' (the caller then uses the role-free prompt)."""
    ids = list(dict.fromkeys(str(e['speaker_id']) for e in entries))
    score = {i: sum(role_score(e['transcript']) for e in entries if str(e['speaker_id']) == i) for i in ids}
    top = sorted(score.values(), reverse=True)
    clinician = max(score, key=score.get) if len(ids) >= 2 and top[0] > top[1] else None
    return [Utterance(id=f'u{n}', text=e['transcript'].strip(),
                      speaker='unknown' if clinician is None else ('clinician' if str(e['speaker_id']) == clinician else 'patient'),
                      start_s=e.get('start_time_seconds'), end_s=e.get('end_time_seconds'))
            for n, e in enumerate(entries, 1)]


def _mock(filename):
    s = mock_data.SCENARIOS[mock_data.scenario_for_filename(filename)]
    out = {'transcript': s['transcript'], 'language': s['language'], 'utterances': []}
    if config.ENABLE_DIARIZATION:  # canned turns from the labelled mock transcript
        turns = re.findall(r'(Doctor|Nurse|Patient):\s*(.*?)(?=\s(?:Doctor|Nurse|Patient):|$)', s['transcript'])
        out['utterances'] = [Utterance(id=f'u{n}', speaker=ROLE_LABELS[w.lower()], text=t.strip()) for n, (w, t) in enumerate(turns, 1)]
    return out


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
        notice = ''
        if config.ENABLE_DIARIZATION and ext in ACCEPTED_EXT:  # Batch API job; no 30 s limit
            try:
                d = sarvam_client.stt_diarized(src, keyterms=formulary.key_terms() if config.ENABLE_KEYTERMS else None)
                return {'transcript': d['transcript'], 'language': d['language'], 'utterances': assign_roles(d['entries'])}
            except sarvam_client.SarvamError:
                notice = 'Speaker separation is unavailable right now; transcribed without speaker labels.'
        if ext in ACCEPTED_EXT and duration is not None and duration <= REST_MAX_S:
            return {**_stt(src), 'utterances': [], 'notice': notice}

        # Unknown duration (browser WebM), unaccepted format, or longer than one request allows.
        wav = tmp / 'audio.wav'
        to_wav(src, wav)
        duration = probe_duration(wav)
        if duration > config.MAX_AUDIO_SECONDS:
            raise AudioTooLongError(f'Audio is longer than {config.MAX_AUDIO_SECONDS} seconds.')
        if duration <= REST_MAX_S:
            return {**_stt(wav), 'utterances': [], 'notice': notice}

        results = []
        for i, (a, b) in enumerate(plan_chunks(duration, find_silences(wav))):
            part = tmp / f'part{i}.wav'
            _cut(wav, a, b, part)
            results.append(_stt(part))
        langs = [r['language'] for r in results if r['language']]
        return {
            'transcript': ' '.join(r['transcript'].strip() for r in results if r['transcript'].strip()),
            'language': Counter(langs).most_common(1)[0][0] if langs else '',
            'utterances': [], 'notice': notice,
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
