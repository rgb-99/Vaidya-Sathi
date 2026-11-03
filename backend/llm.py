"""LLM steps: structure() now; summarize() arrives in M3."""
import json
import logging
import re

from pydantic import ValidationError

import config
import formulary
import mock_data
import sarvam_client
from schemas import ClinicalRecord

log = logging.getLogger('vaidya')
PROMPT_VERSION = 'v1'
SHAPE_KEYS = ['patient', 'chief_complaints', 'vitals', 'diagnosis', 'prescription', 'advice', 'follow_up', 'language_detected']

# SPEC TRD 8.1, plus one line on spoken numbers (STT writes them as words; see DECISIONS.md).
EXTRACTION_PROMPT = (
    'You are a clinical documentation assistant for Indian clinics. The input is a transcript of a doctor-patient '
    'or nurse-patient conversation, possibly mixing Marathi, Hindi, and English. Extract ONLY information explicitly '
    'stated. Never guess, infer, or add drugs, doses, diagnoses, or vitals that were not said. If a field is not '
    'mentioned, use an empty string or empty list. Keep drug doses exactly as spoken. Translate complaints and advice '
    'into short English phrases. Write spoken numbers as digits (for example "एकशे दोन" or "one hundred two" is 102, '
    '"नव्वद बाय साठ" is 90/60). Write temperature as the number only. Output ONLY valid JSON matching this shape, '
    'with no commentary and no code fences: patient{name,age,sex}, chief_complaints[], vitals{bp,temp,spo2,pulse,'
    'resp_rate,sugar}, diagnosis, prescription[{drug,dose,frequency,timing,duration}], advice[], follow_up, '
    'language_detected.'
)


def _examples():
    out = []
    for sid in ('S1', 'S2'):  # S3 is held out of the prompt so the eval stays honest
        s = mock_data.SCENARIOS[sid]
        rec = ClinicalRecord(**s['record']).model_dump()
        out.append(f"Example transcript:\n{s['transcript']}\nExample output:\n"
                   + json.dumps({k: rec[k] for k in SHAPE_KEYS}, ensure_ascii=False))
    return '\n\n'.join(out)


def system_prompt():
    return EXTRACTION_PROMPT + '\n\n' + _examples()


def parse_json(text):
    """Strip reasoning blocks and code fences, then parse the outermost JSON object."""
    text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.S)
    text = re.sub(r'```(?:json)?', '', text)
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < a:
        raise ValueError('no JSON object in model output')
    return json.loads(text[a:b + 1])


def structure(transcript):
    """Transcript -> ClinicalRecord. Retries once with the error appended, then returns an empty record + warning."""
    if config.MOCK_MODE:
        return mock_data.scenario_record(mock_data.scenario_for_transcript(transcript))
    user, err = transcript, ''
    for attempt in range(2):
        try:
            raw = sarvam_client.chat(config.LLM_MODEL, system_prompt(), user, temperature=0, max_tokens=4096)
            data = parse_json(raw)
            data.pop('red_flags', None)  # red flags come only from the deterministic rules
            rec = ClinicalRecord.model_validate(data)
            for rx in rec.prescription:
                rx.drug = formulary.normalize(rx.drug)
            return rec
        except (ValueError, ValidationError) as e:
            err = str(e)[:300]
            log.info('structure attempt %d failed: %s', attempt + 1, err)
            user = f'{transcript}\n\nYour previous output was invalid ({err}). Output ONLY the JSON object.'
    return ClinicalRecord(warnings=['Automatic extraction failed. Please fill the form by hand from the transcript.'])
