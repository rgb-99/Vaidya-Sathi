"""SQLite helpers (plain sqlite3). Fake data only. DB file lives in data/ which is git-ignored."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'app.db'


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(
        'CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, json TEXT);'
        'CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, created_at TEXT, record_id INTEGER, payload_json TEXT);'
        'CREATE TABLE IF NOT EXISTS consultations(record_id INTEGER PRIMARY KEY, started_at TEXT, signed_at TEXT, duration_s REAL, demo INTEGER, language TEXT, red_flags INTEGER, urgent_flags INTEGER, safety_warnings INTEGER);'
        'CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);'
        'CREATE TABLE IF NOT EXISTS sync_results(client_id TEXT PRIMARY KEY, created_at TEXT, result_json TEXT);'
        'CREATE TABLE IF NOT EXISTS shares(token TEXT PRIMARY KEY, created_at TEXT, expires_at TEXT, payload_json TEXT);')
    return c


def _now():
    return datetime.now(timezone.utc).isoformat()


def save_record(record):
    with _conn() as c:
        return c.execute('INSERT INTO records(created_at, json) VALUES (?, ?)', (_now(), record.model_dump_json())).lastrowid


def get_record(record_id):
    with _conn() as c:
        row = c.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
    return json.loads(row['json']) if row else None


def list_records():
    with _conn() as c:
        rows = c.execute('SELECT * FROM records ORDER BY id DESC').fetchall()
    return [{'id': r['id'], 'created_at': r['created_at'], 'record': json.loads(r['json'])} for r in rows]


def save_ticket(record_id, payload, destination='District Hospital'):
    ticket = {'ticket_id': 'T-' + uuid.uuid4().hex[:8].upper(), 'created_at': _now(),
              'destination': destination, 'payload': payload}
    with _conn() as c:
        c.execute('INSERT INTO tickets(id, created_at, record_id, payload_json) VALUES (?, ?, ?, ?)',
                  (ticket['ticket_id'], ticket['created_at'], record_id, json.dumps({**payload, 'destination': destination})))
    return ticket


def list_tickets():
    with _conn() as c:
        rows = c.execute('SELECT * FROM tickets ORDER BY created_at DESC').fetchall()
    return [{'ticket_id': r['id'], 'created_at': r['created_at'], 'record_id': r['record_id'],
             'payload': json.loads(r['payload_json'])} for r in rows]


def save_share(token, created_at, expires_at, payload_json):
    with _conn() as c:
        c.execute('INSERT INTO shares(token, created_at, expires_at, payload_json) VALUES (?, ?, ?, ?)',
                  (token, created_at, expires_at, payload_json))


def get_share(token):
    with _conn() as c:
        return c.execute('SELECT * FROM shares WHERE token = ?', (token,)).fetchone()


def get_sync(client_id):
    with _conn() as c:
        row = c.execute('SELECT result_json FROM sync_results WHERE client_id = ?', (client_id,)).fetchone()
    return json.loads(row['result_json']) if row else None


def save_sync(client_id, result):
    """Idempotent: the first result for an id wins. Only the transcript result is stored, never the audio."""
    with _conn() as c:
        c.execute('INSERT OR IGNORE INTO sync_results(client_id, created_at, result_json) VALUES (?, ?, ?)',
                  (client_id, _now(), json.dumps(result, ensure_ascii=False)))


def save_consultation(record_id, started_at, signed_at, duration_s, demo, language, red_flags, urgent_flags, safety_warnings):
    with _conn() as c:
        c.execute('INSERT OR REPLACE INTO consultations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                  (record_id, started_at, signed_at, duration_s, int(demo), language, red_flags, urgent_flags, safety_warnings))


def list_consultations():
    with _conn() as c:
        return [dict(r) for r in c.execute('SELECT * FROM consultations ORDER BY record_id').fetchall()]


def get_setting(key):
    with _conn() as c:
        row = c.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    return row['value'] if row else None


def set_setting(key, value):
    with _conn() as c:
        c.execute('INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)', (key, str(value)))
