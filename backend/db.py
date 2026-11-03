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
        'CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, created_at TEXT, record_id INTEGER, payload_json TEXT);')
    return c


def _now():
    return datetime.now(timezone.utc).isoformat()


def save_record(record):
    with _conn() as c:
        return c.execute('INSERT INTO records(created_at, json) VALUES (?, ?)', (_now(), record.model_dump_json())).lastrowid


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
