import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def _bool(name, default='false'):
    return os.getenv(name, default).strip().lower() in ('1', 'true', 'yes')


SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
MOCK_MODE = _bool('MOCK_MODE')

STT_MODEL = os.getenv('STT_MODEL', 'saaras:v4')
STT_MODE = os.getenv('STT_MODE', 'transcribe')
LLM_MODEL = os.getenv('LLM_MODEL', 'sarvam-105b')
LLM_MODEL_CONVERSATION = os.getenv('LLM_MODEL_CONVERSATION', 'sarvam-105b-conversations')
TTS_MODEL = os.getenv('TTS_MODEL', 'bulbul:v4-flash')
# Voices for languages beyond mr/hi/en were accepted by the live API for bulbul:v4-flash on 2026-11-03 but not
# auditioned. ml-IN and od-IN are listed by Bulbul but no voice name was accepted, so they are left out.
_VERIFIED_EXTRA = {'bn-IN': 'arnab_bn_conversation', 'gu-IN': 'bhavik_gu_conversation', 'kn-IN': 'chaitra_kn_conversation',
                   'pa-IN': 'anand_pa_conversation', 'ta-IN': 'gokul_ta_narration', 'te-IN': 'kavitha_te_conversation'}
TTS_SPEAKERS = {
    **_VERIFIED_EXTRA,
    'mr-IN': os.getenv('TTS_SPEAKER_MR', ''),
    'hi-IN': os.getenv('TTS_SPEAKER_HI', ''),
    'en-IN': os.getenv('TTS_SPEAKER_EN', ''),
}
LANGUAGES = {'mr-IN': 'Marathi', 'hi-IN': 'Hindi', 'en-IN': 'English', 'bn-IN': 'Bengali', 'gu-IN': 'Gujarati',
             'kn-IN': 'Kannada', 'pa-IN': 'Punjabi', 'ta-IN': 'Tamil', 'te-IN': 'Telugu'}

DEFAULT_LANG = os.getenv('DEFAULT_LANG', 'mr-IN')
MAX_AUDIO_SECONDS = int(os.getenv('MAX_AUDIO_SECONDS', '180'))
CORS_ORIGIN = os.getenv('CORS_ORIGIN', 'http://localhost:5173')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', 'http://localhost:5173')
SHARE_TOKEN_TTL_DAYS = int(os.getenv('SHARE_TOKEN_TTL_DAYS', '7'))

PRODUCTION_MODE = _bool('PRODUCTION_MODE')   # true: safety rules without a reviewer are ignored
ENABLE_DIARIZATION = _bool('ENABLE_DIARIZATION')
ENABLE_KEYTERMS = _bool('ENABLE_KEYTERMS')
ENABLE_STREAMING = _bool('ENABLE_STREAMING')
ENABLE_VISION = _bool('ENABLE_VISION')
EVAL_SCENARIO_FILE = os.getenv('EVAL_SCENARIO_FILE', 'eval/scenarios.jsonl')
