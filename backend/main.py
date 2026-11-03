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
import voice
from schemas import (AlertAudioRequest, ClinicalRecord, ReferralRequest, StructureRequest,
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
def structure(req: StructureRequest):
    require_mock('/api/structure')
    with timed('structure'):
        return mock_data.scenario_record(mock_data.scenario_for_transcript(req.transcript))


@app.post('/api/redflags')
def redflags(record: ClinicalRecord):
    require_mock('/api/redflags')
    with timed('redflags'):
        # Canned: the mock rule set only fires for S2's vitals (real engine is M4).
        v = record.vitals
        if v.bp == '90/60' and v.temp == '102' and v.pulse == '118':
            return {'red_flags': mock_data.scenario_record('S2').red_flags}
        return {'red_flags': []}


@app.post('/api/summary', response_model=SummaryResponse)
def summary(req: SummaryRequest):
    require_mock('/api/summary')
    with timed('summary'):
        text = mock_data.SUMMARIES[mock_data.scenario_for_record(req.record)][req.language]
        audio = sarvam_client.tts(text, req.language)
        return SummaryResponse(text=text, language=req.language,
                               audio_base64=base64.b64encode(audio).decode())


@app.post('/api/alert-audio')
def alert_audio(req: AlertAudioRequest):
    require_mock('/api/alert-audio')
    with timed('alert-audio'):
        text = mock_data.ALERT_TEXTS.get(req.language, mock_data.ALERT_TEXTS['en-IN'])
        audio = sarvam_client.tts(text, req.language)
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
