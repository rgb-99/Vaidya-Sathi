"""Speak a phrase with one voice to listen to it. Run from repo root:
python scripts/test_voice.py mr-IN ishita_mr_conversational "नमस्कार"   -> writes voice_test_<lang>_<speaker>.wav"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

import config
import sarvam_client

if len(sys.argv) != 4:
    sys.exit(__doc__)
lang, speaker, text = sys.argv[1:]
config.MOCK_MODE = False
out = Path(f'voice_test_{lang}_{speaker}.wav')
out.write_bytes(sarvam_client.tts(text, lang, speaker=speaker))
print(f'wrote {out} ({out.stat().st_size} bytes)')
