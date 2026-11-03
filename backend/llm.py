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


# ---------------------------------------------------------------- summary (M3)
LANG_NAMES = {'mr-IN': 'Marathi', 'hi-IN': 'Hindi', 'en-IN': 'English'}
MAX_WORDS = 120

# SPEC TRD 8.2, plus two lines to keep the machine post-check reliable.
SUMMARY_PROMPT = (
    'You write medicine instructions for patients in India. Language: {language}. Use very simple spoken words a '
    '65-year-old with little schooling can follow. Use ONLY the diagnosis, medicines, doses, timings, and advice in the '
    'provided JSON. Do not add or change any medicine, dose, or advice. Do not use abbreviations like OD or BD. '
    'Structure: one sentence on what the doctor found; then Morning, Afternoon, Night, listing which medicine and how '
    'many tablets or how much; then simple advice; then when to come back. Maximum 120 words. End with: if you feel '
    'worse, go to the hospital immediately. Write medicine names and doses exactly as in the JSON, in Latin letters '
    'and digits (for example "Metoprolol 50mg"). Write every other word in {language}, including the words for morning, '
    'afternoon, night and the final sentence. Output only the instructions, no preface.'
)
ABBREVIATIONS = re.compile(r'\b(OD|BD|TDS|QID|SOS|HS|BID|TID)\b')
DOSE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b', re.I)


def _dose_key(num, unit):
    return f'{float(num):g}{unit.lower()}'


def check_summary(text, record):
    """Return a list of problems; empty means the summary only restates the prescription."""
    problems, low = [], text.lower()
    rx = [r for r in record.prescription if r.drug.strip()]
    for r in rx:
        if r.drug.lower() not in low:
            problems.append(f'drug missing: {r.drug}')
    allowed = {r.drug.lower() for r in rx}
    for d in formulary.DRUGS:
        if re.search(rf'\b{re.escape(d.lower())}\b', low) and d.lower() not in allowed:
            problems.append(f'drug not prescribed: {d}')
    want = {_dose_key(*m.groups()) for r in rx for m in DOSE_RE.finditer(r.dose)}
    got = {_dose_key(*m.groups()) for m in DOSE_RE.finditer(text)}
    problems += [f'dose not prescribed: {d}' for d in got - want]
    problems += [f'dose missing: {d}' for d in want - got]
    if len(text.split()) > MAX_WORDS:
        problems.append('over 120 words')
    if ABBREVIATIONS.search(text):
        problems.append('abbreviation used')
    return problems


# Fixed phrase dictionary for the template fallback (SPEC 8.3). Unknown words are left as the clinician wrote them.
PHRASES = {
    'mr-IN': {'take': 'घ्या', 'for': 'साठी', 'advice': 'सल्ला', 'return': 'पुन्हा या', 'none': 'डॉक्टरांनी कोणतीही औषधे सांगितलेली नाहीत.',
              'worse': 'बरे वाटत नसेल तर लगेच दवाखान्यात जा.',
              'words': {'once daily': 'दिवसातून एकदा', 'twice daily': 'दिवसातून दोनदा', 'thrice daily': 'दिवसातून तीनदा', 'morning': 'सकाळी',
                        'afternoon': 'दुपारी', 'evening': 'संध्याकाळी', 'night': 'रात्री', 'after food': 'जेवणानंतर', 'after meals': 'जेवणानंतर',
                        'after dinner': 'रात्रीच्या जेवणानंतर', 'before food': 'जेवणापूर्वी', 'and': 'आणि', 'days': 'दिवस', 'weeks': 'आठवडे',
                        'day': 'दिवस', 'week': 'आठवडा'}},
    'hi-IN': {'take': 'लीजिए', 'for': 'के लिए', 'advice': 'सलाह', 'return': 'दोबारा आइए', 'none': 'डॉक्टर ने कोई दवा नहीं बताई है।',
              'worse': 'तबीयत ख़राब लगे तो तुरंत अस्पताल जाइए।',
              'words': {'once daily': 'दिन में एक बार', 'twice daily': 'दिन में दो बार', 'thrice daily': 'दिन में तीन बार', 'morning': 'सुबह',
                        'afternoon': 'दोपहर', 'evening': 'शाम', 'night': 'रात', 'after food': 'खाने के बाद', 'after meals': 'खाने के बाद',
                        'after dinner': 'रात के खाने के बाद', 'before food': 'खाने से पहले', 'and': 'और', 'days': 'दिन', 'weeks': 'हफ्ते',
                        'day': 'दिन', 'week': 'हफ्ता'}},
    'en-IN': {'take': 'Take', 'for': 'for', 'advice': 'Advice', 'return': 'Follow-up', 'none': 'The doctor has not prescribed any medicines.',
              'worse': 'If you feel worse, go to the hospital immediately.', 'words': {}},
}


def _tr(text, lang):
    out = text.strip()
    for en, local in sorted(PHRASES[lang]['words'].items(), key=lambda kv: -len(kv[0])):
        out = re.sub(rf'\b{re.escape(en)}\b', local, out, flags=re.I)
    return out


def template_summary(record, lang):
    p = PHRASES[lang]
    lines = []
    for r in record.prescription:
        if not r.drug.strip():
            continue
        parts = [_tr(x, lang) for x in (r.frequency, r.timing) if x]
        dur = f"{_tr(r.duration, lang)} {p['for']}" if r.duration else ''
        if lang == 'en-IN':
            lines.append(f"{p['take']} {r.drug} {r.dose} {' '.join(parts)} {('for ' + r.duration) if r.duration else ''}".strip() + '.')
        else:
            lines.append(f"{r.drug} {r.dose} {' '.join(parts)} {dur} {p['take']}.".replace('  ', ' '))
    lines = lines or [p['none']]
    if record.advice:
        lines.append(f"{p['advice']}: " + '; '.join(_tr(a, lang) for a in record.advice) + '.')
    if record.follow_up:
        lines.append(f"{p['return']}: {_tr(record.follow_up, lang)}.")
    lines.append(p['worse'])
    return ' '.join(lines)


def summarize(record, language):
    """Returns (text, used_fallback). Regenerates once if the post-check fails, then uses the template."""
    if config.MOCK_MODE:
        return mock_data.SUMMARIES[mock_data.scenario_for_record(record)][language], False
    payload = json.dumps({k: record.model_dump()[k] for k in ('diagnosis', 'prescription', 'advice', 'follow_up')},
                         ensure_ascii=False)
    system = SUMMARY_PROMPT.format(language=LANG_NAMES[language])
    for attempt in range(2):
        try:
            text = (sarvam_client.chat(config.LLM_MODEL_CONVERSATION, system, payload, temperature=0.2, max_tokens=2048) or '')
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
        except sarvam_client.SarvamError:
            raise
        text = re.sub(r'\s*\n\s*', ' ', text)
        if language != 'en-IN':  # the closing safety sentence is fixed, so never leave it in English
            text = re.sub(r'(?is)\s*if you feel worse.*$', '', text).strip()
            if not re.search(r'(?:ख़राब|खराब|तुरंत|लगेच)', text[-60:]):
                text = f"{text} {PHRASES[language]['worse']}"
        problems = check_summary(text, record) if text else ['empty output']
        if not problems:
            return text, False
        log.info('summary attempt %d rejected: %s', attempt + 1, problems)
    return template_summary(record, language), True
