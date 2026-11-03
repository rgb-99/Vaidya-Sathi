"""Make synthetic demo clips from demo/transcripts/*.txt with Bulbul. Run from repo root:
python scripts/synthesize_demo_clips.py   (needs a real key; MOCK_MODE is ignored)"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import config
import sarvam_client

# Speakers verified against the live API on 2026-11-03 (bulbul:v4-flash).
CLIPS = {
    'S1': ('mr-IN', 'ishita_mr_conversational'),
    'S2': ('mr-IN', 'nilesh_mr_conversation'),
    'S3': ('hi-IN', 'rahul_hi_conversational'),
}

config.MOCK_MODE = False
for sid, (lang, speaker) in CLIPS.items():
    text = (ROOT / 'demo' / 'transcripts' / f'{sid}.txt').read_text(encoding='utf-8').strip()
    wav = sarvam_client.tts(text, lang, speaker=speaker)
    out = ROOT / 'demo' / 'audio' / f'{sid}.wav'
    out.write_bytes(wav)
    print(f'{out.relative_to(ROOT)}: {len(wav)} bytes ({lang}, {speaker})')
