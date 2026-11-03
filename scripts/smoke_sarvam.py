"""Sarvam onboarding smoke test: one chat call. Run from repo root: python scripts/smoke_sarvam.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

import config
import sarvam_client

if not config.SARVAM_API_KEY:
    sys.exit('SARVAM_API_KEY is empty. Paste your key into .env and run again.')

config.MOCK_MODE = False  # smoke test always hits the real API
try:
    reply = sarvam_client.chat(
        config.LLM_MODEL_CONVERSATION,
        'You are a helpful assistant.',
        'Say hello in one short sentence in Marathi.',
    )
except sarvam_client.SarvamError as e:
    sys.exit(f'Sarvam error: {e}')
print(f'Model: {config.LLM_MODEL_CONVERSATION}')
print(f'Reply: {reply}')
