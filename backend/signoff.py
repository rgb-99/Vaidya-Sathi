"""Clinician sign-off: an HMAC over the record, made with a server-side key, so the API can verify that a
record it receives was signed and not edited since. The key is SIGNING_KEY when set (hosts that run several
instances), otherwise data/signing.key (git-ignored)."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import config
import db

# Derived or display-only fields are not part of what the clinician signed.
UNSIGNED_FIELDS = {'signature', 'red_flags', 'safety_warnings', 'warnings'}


def _key():
    if config.SIGNING_KEY:
        return config.SIGNING_KEY.encode()
    path = db.DB_PATH.parent / 'signing.key'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip().encode()


def _digest(record):
    body = json.dumps(record.model_dump(exclude=UNSIGNED_FIELDS), sort_keys=True, ensure_ascii=False)
    return hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()


def sign(record, clinician_name):
    name = (clinician_name or '').strip()
    if not name:
        raise ValueError('Clinician name is required to sign off.')
    signed = record.model_copy(deep=True)
    signed.signed_off_by = name
    signed.signed_at = datetime.now(timezone.utc).isoformat()  # set only here, never by the LLM
    signed.signature = _digest(signed)
    return signed


def is_signed(record):
    return bool(record.signature and record.signed_off_by and record.signed_at
                and hmac.compare_digest(record.signature, _digest(record)))
