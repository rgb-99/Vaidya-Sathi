import asyncio
import base64
import json
import logging
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

import card
import config
import db
import export
import ics
import mock_data
import sarvam_client
import llm
import redflags
import safety
import share
import signoff
import vision
import voice
from schemas import (AlertAudioRequest, ClinicalRecord, ReferralRequest, ReconcileRequest, ShareRequest, StructureRequest,
                     SignoffRequest, SummaryRequest, SummaryResponse)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('vaidya')

app = FastAPI(title='Vaidya Saathi')
app.add_middleware(CORSMiddleware, allow_origins=[config.CORS_ORIGIN],
                   allow_methods=['*'], allow_headers=['*'])


@contextmanager
def timed(step):
    """Log each pipeline step with its duration."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        log.info('step=%s duration_ms=%d', step, (time.perf_counter() - t0) * 1000)


def require_signed(record):
    """Server-side gate: summary audio, referral, export and share need a verified clinician sign-off."""
    if not signoff.is_signed(record):
        raise HTTPException(403, 'Clinician sign-off is required (and the record must not change after signing).')


def require_mock(route):
    """Routes not yet implemented for real return 501 when MOCK_MODE=false."""
    if not config.MOCK_MODE:
        raise HTTPException(501, f'{route} is not implemented yet. Set MOCK_MODE=true to use canned data.')


app.mount('/demo/audio', StaticFiles(directory=Path(__file__).resolve().parent.parent / 'demo' / 'audio'),
          name='demo-audio')


@app.exception_handler(StarletteHTTPException)
async def http_error(_, exc):
    return JSONResponse({'error': str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_, exc):
    return JSONResponse({'error': 'Invalid request.'}, status_code=422)


@app.exception_handler(voice.AudioError)
async def audio_error(_, exc):
    return JSONResponse({'error': str(exc)}, status_code=exc.status_code)


@app.exception_handler(sarvam_client.SarvamError)
async def sarvam_error(_, exc):
    return JSONResponse({'error': str(exc)}, status_code=exc.status_code)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mock': config.MOCK_MODE}


@app.post('/api/transcribe')
async def transcribe(audio: UploadFile = File(...)):
    with timed('transcribe'):
        return await run_in_threadpool(voice.transcribe, await audio.read(), audio.filename)


@app.post('/api/sync')
async def sync(client_id: str = Form(...), audio: UploadFile = File(...)):
    """Transcribe a recording that was queued offline. Idempotent: the client-generated id means a retried or
    repeated upload returns the stored result instead of transcribing (and paying for) the audio again."""
    if not re.fullmatch(r'[\w-]{8,64}', client_id):
        raise HTTPException(400, 'Invalid client id.')
    stored = db.get_sync(client_id)
    if stored is not None:
        return {**stored, 'duplicate': True}
    with timed('sync'):
        result = jsonable_encoder(await run_in_threadpool(voice.transcribe, await audio.read(), audio.filename))
    db.save_sync(client_id, result)
    return {**result, 'duplicate': False}


@app.post('/api/structure')
async def structure(req: StructureRequest):
    with timed('structure'):
        rec = await run_in_threadpool(llm.structure, req.transcript, req.utterances)
    with timed('redflags'):
        rec.red_flags = redflags.check(rec)
    rec.safety_warnings = safety.check(rec)
    return rec


@app.post('/api/redflags')
def redflags_route(record: ClinicalRecord):
    with timed('redflags'):
        return {'red_flags': redflags.check(record)}


@app.post('/api/summary', response_model=SummaryResponse)
async def summary(req: SummaryRequest):
    require_signed(req.record)
    if req.language not in config.LANGUAGES:
        raise HTTPException(400, f'Unsupported language {req.language}.')
    with timed('summary'):
        text, fallback = await run_in_threadpool(llm.summarize, req.record, req.language)
    spoken = llm.spoken_language(req.language, fallback)
    with timed('speak'):
        try:
            audio = await run_in_threadpool(voice.speak, text, spoken)
            return SummaryResponse(text=text, language=spoken, used_fallback=fallback,
                                   audio_base64=base64.b64encode(audio).decode())
        except sarvam_client.SarvamError as e:  # keep the text so the clinician can still read it out
            return SummaryResponse(text=text, language=spoken, used_fallback=fallback,
                                   audio_base64='', audio_error=str(e))


@app.post('/api/alert-audio')
async def alert_audio(req: AlertAudioRequest):
    text = redflags.alert_text(req.red_flags, req.language)
    if not text:
        raise HTTPException(400, 'No red flags to announce.')
    with timed('alert-audio'):
        lang = req.language if req.language in ('mr-IN', 'hi-IN', 'en-IN') else 'en-IN'
        audio = await run_in_threadpool(voice.speak, text, lang)
        return {'text': text, 'audio_base64': base64.b64encode(audio).decode()}


@app.post('/api/referral')
def referral(req: ReferralRequest):
    if req.confirmed is not True:
        raise HTTPException(400, 'Referral requires confirmed=true.')
    require_signed(req.record)
    with timed('referral'):
        rec = req.record
        record_id = req.record_id if req.record_id is not None else db.save_record(rec)
        return db.save_ticket(record_id, {
            'patient': rec.patient.model_dump(),
            'vitals': rec.vitals.model_dump(),
            'red_flags': [f.model_dump() for f in rec.red_flags],
        })


@app.post('/api/signoff')
def sign_off(req: SignoffRequest):
    """Locks the record: sets signed_off_by, signed_at and the signature, and saves it to history."""
    try:
        signed = signoff.sign(req.record, req.clinician_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {'record': signed, 'id': db.save_record(signed)}


@app.get('/api/export/{record_id}.json')
def export_record(record_id: int):
    data = db.get_record(record_id)
    if data is None:
        raise HTTPException(404, 'Record not found.')
    record = ClinicalRecord.model_validate(data)
    require_signed(record)
    return export.bundle(record, record_id)


@app.get('/api/records')
def records():
    return db.list_records()


@app.get('/api/tickets')
def tickets():
    return db.list_tickets()


def require_vision():
    if not config.ENABLE_VISION:
        raise HTTPException(503, 'Prescription photo reading is turned off (set ENABLE_VISION=true).')


@app.get('/api/features')
def features():
    return {'vision': config.ENABLE_VISION, 'diarization': config.ENABLE_DIARIZATION, 'streaming': config.ENABLE_STREAMING}


@app.post('/api/prescription-photo')
async def prescription_photo(image: UploadFile = File(...)):
    require_vision()
    try:
        return {'job_id': vision.start(image.filename, await image.read())}
    except vision.VisionError as e:
        raise HTTPException(e.status_code, str(e))


@app.get('/api/prescription-photo/{job_id}')
def prescription_photo_result(job_id: str):
    require_vision()
    job = vision.status(job_id)
    if job is None:
        raise HTTPException(404, 'Unknown job.')
    return {'job_id': job_id, **job}


@app.post('/api/reconcile')
def reconcile(req: ReconcileRequest):
    return {'lines': vision.reconcile(req.previous, req.record)}


@app.websocket('/api/stream')
async def stream(ws: WebSocket, language: str = 'unknown', scenario: str = 'S1'):
    """Relay microphone audio to Sarvam real-time STT. The browser sends 16 kHz mono WAV chunks (binary) and the text
    'end' when it stops; it receives {type: 'partial', text} per segment, then {type: 'done', transcript}.
    Gated by ENABLE_STREAMING; the batch path stays the default and the fallback. Audio is never stored."""
    await ws.accept()
    if not config.ENABLE_STREAMING:
        await ws.send_json({'type': 'error', 'error': 'Live streaming is turned off (ENABLE_STREAMING=false). Use the normal recorder.'})
        return await ws.close()
    segments = []

    async def next_audio():
        msg = await ws.receive()
        if msg.get('type') == 'websocket.disconnect' or msg.get('text') == 'end':
            return None
        return msg.get('bytes') or b''

    async def emit(text):
        segments.append(text)
        await ws.send_json({'type': 'partial', 'text': text})

    try:
        if config.MOCK_MODE:   # canned words, one segment per chunk received, no network
            words = mock_data.SCENARIOS.get(scenario, mock_data.SCENARIOS['S1'])['transcript'].split()
            per, i = 4, 0
            while await next_audio() is not None:   # one segment per chunk, until the client sends 'end'
                if i < len(words):
                    await emit(' '.join(words[i:i + per]))
                    i += per
        else:
            await sarvam_client.stream_relay(next_audio, emit, language)
        await ws.send_json({'type': 'done', 'transcript': ' '.join(segments)})
    except sarvam_client.SarvamError as e:
        await ws.send_json({'type': 'error', 'error': str(e)})
    except WebSocketDisconnect:
        return
    await ws.close()


@app.post('/api/safety')
def safety_route(record: ClinicalRecord):
    """Prescription safety warnings for the clinician. Never changes the prescription."""
    return {'safety_warnings': safety.check(record)}


@app.post('/api/share')
async def create_share(req: ShareRequest):
    require_signed(req.record)
    if req.language not in config.LANGUAGES:
        raise HTTPException(400, f'Unsupported language {req.language}.')
    text, fallback = await run_in_threadpool(llm.summarize, req.record, req.language)
    spoken = llm.spoken_language(req.language, fallback)
    try:
        audio = base64.b64encode(await run_in_threadpool(voice.speak, text, spoken)).decode()
    except sarvam_client.SarvamError:
        audio = ''   # the page still shows the written schedule
    return share.create(req.record, text, audio, spoken, req.include_diagnosis)


@app.get('/api/share/{token}')
def public_share(token: str, request: Request):
    """Public, read-only. 404 when unknown or expired. Not indexed, not cached, rate-limited."""
    headers = {'X-Robots-Tag': 'noindex, nofollow', 'Cache-Control': 'no-store'}
    if not share.allow(request.client.host if request.client else 'unknown'):
        return JSONResponse({'error': 'Too many requests. Try again in a minute.'}, status_code=429, headers=headers)
    payload = share.get(token)
    if payload is None:
        return JSONResponse({'error': 'This link has expired or does not exist.'}, status_code=404, headers=headers)
    return JSONResponse(payload, headers=headers)


@app.get('/api/schedule.ics')
def schedule_ics(record_id: int):
    data = db.get_record(record_id)
    if data is None:
        raise HTTPException(404, 'Record not found.')
    record = ClinicalRecord.model_validate(data)
    require_signed(record)
    return Response(ics.build(record), media_type='text/calendar',
                    headers={'Content-Disposition': 'attachment; filename="medicine-reminders.ics"'})


@app.post('/api/card', response_class=HTMLResponse)
def prescription_card(record: ClinicalRecord):
    return card.render_card(record)


@app.get('/api/eval/latest')
def eval_latest():
    path = Path(__file__).resolve().parent.parent / 'eval' / 'reports' / 'latest.json'
    if not path.exists():
        raise HTTPException(404, 'No evaluation report yet. Run: python eval/run_eval.py --all')
    return json.loads(path.read_text(encoding='utf-8'))


@app.get('/api/languages')
def languages():
    """Languages with a verified voice. Malayalam and Odia are listed by Bulbul but no voice name was accepted."""
    return [{'code': c, 'name': n} for c, n in config.LANGUAGES.items() if config.TTS_SPEAKERS.get(c)]


@app.get('/api/demo/scenarios')
def demo_scenarios():
    """S1 to S3 with their prerecorded clip (demo/audio/<id>.wav) so the picker can run the whole pipeline."""
    demo = Path(__file__).resolve().parent.parent / 'demo'
    out = []
    for sid, s in mock_data.SCENARIOS.items():
        ref = demo / 'transcripts' / f'{sid}.txt'
        out.append({
            'id': sid, 'title': s['title'],
            'audio_url': f'/demo/audio/{sid}.wav' if (demo / 'audio' / f'{sid}.wav').exists() else '',
            'transcript': s['transcript'] if config.MOCK_MODE or not ref.exists() else ref.read_text(encoding='utf-8').strip(),
        })
    return out
