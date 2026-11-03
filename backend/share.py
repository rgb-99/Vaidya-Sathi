"""Patient share page (F22): 128-bit tokens, expiry, a public payload that holds only what the patient needs."""
import base64
import io
import json
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import segno

import card
import config
import db

RATE_LIMIT, RATE_WINDOW_S = 30, 60
_hits = defaultdict(deque)


def allow(client):
    """In-memory sliding-window limit for the public endpoint."""
    now, q = time.monotonic(), _hits[client]
    while q and now - q[0] > RATE_WINDOW_S:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return False
    q.append(now)
    return True


def qr_png_base64(url):
    buf = io.BytesIO()
    segno.make(url, error='m').save(buf, kind='png', scale=6, border=2)
    return base64.b64encode(buf.getvalue()).decode()


def public_payload(record, summary_text, audio_base64, language, include_diagnosis, expires_at):
    """Everything the public page may show. No vitals, no last name, no clinician name, no history."""
    grid, other = card.slots(record)
    names = record.patient.name.split()
    return {
        'first_name': names[0] if names else '',
        'language': language,
        'schedule': {k: [{'medicine': a, 'detail': b} for a, b in v] for k, v in {**grid, 'other': other}.items()},
        'advice': record.advice, 'follow_up': record.follow_up,
        'diagnosis': record.diagnosis if include_diagnosis else '',
        'summary_text': summary_text, 'audio_base64': audio_base64, 'expires_at': expires_at,
    }


def create(record, summary_text, audio_base64, language, include_diagnosis=False, now=None):
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(16)          # 128 random bits, URL-safe
    expires = (now + timedelta(days=config.SHARE_TOKEN_TTL_DAYS)).isoformat()
    payload = public_payload(record, summary_text, audio_base64, language, include_diagnosis, expires)
    db.save_share(token, now.isoformat(), expires, json.dumps(payload, ensure_ascii=False))
    url = f'{config.PUBLIC_BASE_URL}/share/{token}'
    return {'token': token, 'url': url, 'qr_png_base64': qr_png_base64(url), 'expires_at': expires}


def get(token, now=None):
    """The public payload, or None if the token is unknown or expired."""
    row = db.get_share(token)
    if not row or datetime.fromisoformat(row['expires_at']) <= (now or datetime.now(timezone.utc)):
        return None
    return json.loads(row['payload_json'])
