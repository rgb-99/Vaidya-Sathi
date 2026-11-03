import base64
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

import card
import config
import db
import export
import mock_data
import sarvam_client
import llm
import redflags
import signoff
import voice
from schemas import (AlertAudioRequest, ClinicalRecord, ReferralRequest, StructureRequest,
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


@app.post('/api/structure')
async def structure(req: StructureRequest):
    with timed('structure'):
        rec = await run_in_threadpool(llm.structure, req.transcript)  # also stores the transcript in rec.utterances
    with timed('redflags'):
        rec.red_flags = redflags.check(rec)
    return rec


@app.post('/api/redflags')
def redflags_route(record: ClinicalRecord):
    with timed('redflags'):
        return {'red_flags': redflags.check(record)}


@app.post('/api/summary', response_model=SummaryResponse)
async def summary(req: SummaryRequest):
    require_signed(req.record)
    with timed('summary'):
        text, fallback = await run_in_threadpool(llm.summarize, req.record, req.language)
    with timed('speak'):
        try:
            audio = await run_in_threadpool(voice.speak, text, req.language)
            return SummaryResponse(text=text, language=req.language, used_fallback=fallback,
                                   audio_base64=base64.b64encode(audio).decode())
        except sarvam_client.SarvamError as e:  # keep the text so the clinician can still read it out
            return SummaryResponse(text=text, language=req.language, used_fallback=fallback,
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


@app.post('/api/card', response_class=HTMLResponse)
def prescription_card(record: ClinicalRecord):
    return card.render_card(record)


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
