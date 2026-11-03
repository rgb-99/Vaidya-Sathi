"""Prescription photo reading with Sarvam Document AI (F15) and reconciliation against today's record (F26).
Fake prescriptions only. Reading is asynchronous: a job id is returned at once and polled."""
import json
import threading
import time
import uuid

import config
import formulary
import sarvam_client

SCHEMA = json.dumps({'type': 'object', 'properties': {'medicines': {'type': 'array', 'items': {'type': 'object', 'properties': {
    'drug': {'type': 'string'}, 'dose': {'type': 'string'}, 'frequency': {'type': 'string'}, 'duration': {'type': 'string'}}}}}})
MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.pdf': 'application/pdf'}
MAX_BYTES = 10 * 1024 * 1024   # our own limit; the docs pages read did not state one
POLL_TIMEOUT_S = 90
DONE, FAILED = {'completed'}, {'failed', 'error', 'cancelled', 'canceled'}

CANNED = {   # MOCK_MODE results by sample name; confidence is made up for the mock
    'rx1': [('Metoprolol', '50mg', '1 morning', '30 days'), ('Amlodipine', '5mg', '1 night', '30 days')],
    'rx2': [('Metformin', '500mg', '1 morning and evening', '30 days'), ('Atorvastatin', '10mg', '1 night', '30 days')],
    'rx3': [('Paracetamol', '500mg', '1 twice daily', '3 days'), ('Cetirizine', '10mg', '1 night', '5 days')],
}
_jobs = {}


class VisionError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def check_file(filename, data):
    ext = '.' + (filename or '').rsplit('.', 1)[-1].lower() if '.' in (filename or '') else ''
    if ext not in MIME:
        raise VisionError('Upload a PNG, JPG or PDF photo of the prescription.')
    if not data:
        raise VisionError('The uploaded file is empty.')
    if len(data) > MAX_BYTES:
        raise VisionError('The photo is larger than 10 MB.', 413)
    return MIME[ext]


def poll(job_id, timeout=POLL_TIMEOUT_S, sleep=time.sleep, clock=time.monotonic):
    """Wait for the job with a growing delay (1 s up to 5 s). Raises VisionError on failure or timeout."""
    start, delay = clock(), 1.0
    while True:
        status = sarvam_client.doc_status(job_id)
        if status in DONE:
            return
        if status in FAILED:
            raise VisionError('Sarvam could not read this photo.', 502)
        if clock() - start + delay > timeout:
            raise VisionError('Reading the photo took too long. Try again.', 504)
        sleep(delay)
        delay = min(delay + 1, 5.0)


def parse_result(payload):
    """Document AI payload -> [{drug, dose, frequency, duration, confidence}]. Anything malformed is skipped, and a
    payload with no usable medicine raises, so the clinician is told instead of seeing an empty list as 'no drugs'."""
    result, annotations = payload.get('result'), payload.get('annotations') or {}
    meds = result.get('medicines') if isinstance(result, dict) else None
    if not isinstance(meds, list):
        raise VisionError('The photo could not be read as a prescription.', 502)
    notes = annotations.get('medicines') if isinstance(annotations.get('medicines'), list) else []
    items = []
    for i, m in enumerate(meds):
        if not isinstance(m, dict) or not str(m.get('drug') or '').strip():
            continue
        confs = []
        note = notes[i] if i < len(notes) and isinstance(notes[i], dict) else {}
        for field in note.values():
            if isinstance(field, dict) and isinstance(field.get('confidence'), (int, float)):
                confs.append(float(field['confidence']))
        items.append({'drug': formulary.normalize(str(m['drug']).strip()),
                      **{k: str(m.get(k) or '').strip() for k in ('dose', 'frequency', 'duration')},
                      'confidence': round(min(confs), 2) if confs else None})
    if not items:
        raise VisionError('No medicines could be read from the photo.', 502)
    return items


def read_prescription(filename, data):
    """Blocking: start the job, poll, parse. Used by the background worker."""
    mime = check_file(filename, data)
    if config.MOCK_MODE:
        name = (filename or '').rsplit('.', 1)[0].lower()
        rows = CANNED.get(name, CANNED['rx1'])
        return [{'drug': d, 'dose': ds, 'frequency': f, 'duration': du, 'confidence': 0.9} for d, ds, f, du in rows]
    job_id = sarvam_client.doc_extract_start(filename, data, mime, SCHEMA)
    poll(job_id)
    return parse_result(sarvam_client.doc_results(job_id))


def _work(job_id, filename, data):
    try:
        _jobs[job_id].update(status='completed', items=read_prescription(filename, data))
    except (VisionError, sarvam_client.SarvamError) as e:
        _jobs[job_id].update(status='failed', error=str(e))
    except Exception:
        _jobs[job_id].update(status='failed', error='Unexpected error while reading the photo.')


def start(filename, data, background=True):
    """Validate, register a job and run it in the background. Returns the job id."""
    check_file(filename, data)
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {'status': 'pending', 'items': [], 'error': ''}
    if background:
        threading.Thread(target=_work, args=(job_id, filename, data), daemon=True).start()
    else:
        _work(job_id, filename, data)
    return job_id


def status(job_id):
    return _jobs.get(job_id)


# ---- Reconciliation (deterministic; the LLM plays no part)
def _key(name):
    return formulary.normalize(name or '').strip().lower()


def _dose(d):
    return ''.join((d or '').lower().split())


def reconcile(previous, record):
    """Compare an older prescription (photo) with today's record. Nothing is merged; every line is for the clinician
    to accept or reject. status: new (only today), stopped (only on the old one), dose_changed, unchanged."""
    today = {_key(rx.drug): rx for rx in record.prescription if rx.drug.strip()}
    old = {_key(p['drug']): p for p in previous if p.get('drug', '').strip()}
    lines = []
    for k, p in old.items():
        rx = today.get(k)
        if rx is None:
            lines.append({'status': 'stopped', 'drug': p['drug'], 'old_dose': p['dose'], 'new_dose': '', 'confidence': p.get('confidence')})
        elif _dose(rx.dose) != _dose(p['dose']):
            lines.append({'status': 'dose_changed', 'drug': rx.drug, 'old_dose': p['dose'], 'new_dose': rx.dose, 'confidence': p.get('confidence')})
        else:
            lines.append({'status': 'unchanged', 'drug': rx.drug, 'old_dose': p['dose'], 'new_dose': rx.dose, 'confidence': p.get('confidence')})
    for k, rx in today.items():
        if k not in old:
            lines.append({'status': 'new', 'drug': rx.drug, 'old_dose': '', 'new_dose': rx.dose, 'confidence': None})
    return lines
