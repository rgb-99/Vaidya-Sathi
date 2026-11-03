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
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

import config
import mock_data
import sarvam_client
import llm
import redflags
import voice
from schemas import (AlertAudioRequest, ClinicalRecord, ReferralRequest, StructureRequest, Utterance,
                     SummaryRequest, SummaryResponse)

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
        rec = await run_in_threadpool(llm.structure, req.transcript)
        # Keep the transcript on the record so later /redflags re-runs can still see symptom keywords.
        rec.utterances = [Utterance(id='u1', text=req.transcript)]
    with timed('redflags'):
        rec.red_flags = redflags.check(rec)
    return rec


@app.post('/api/redflags')
def redflags_route(record: ClinicalRecord):
    with timed('redflags'):
        return {'red_flags': redflags.check(record)}


@app.post('/api/summary', response_model=SummaryResponse)
async def summary(req: SummaryRequest):
    if not req.confirmed:
        raise HTTPException(400, 'The clinician must confirm the record before a patient summary is generated.')
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
    require_mock('/api/referral')
    with timed('referral'):
        rec = req.record
        return {
            'ticket_id': 'T-' + uuid.uuid4().hex[:8].upper(),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'destination': 'District Hospital',
            'payload': {
                'patient': rec.patient.model_dump(),
                'vitals': rec.vitals.model_dump(),
                'red_flags': [f.model_dump() for f in rec.red_flags],
            },
        }


@app.get('/api/demo/scenarios')
def demo_scenarios():
    require_mock('/api/demo/scenarios')
    return [{'id': sid, 'title': s['title'], 'audio_url': '/demo/audio/mock.wav',
             'transcript': s['transcript']} for sid, s in mock_data.SCENARIOS.items()]


@app.get('/api/records')
def records():
    require_mock('/api/records')
    return []
