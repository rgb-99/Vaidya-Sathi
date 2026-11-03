"""LLM steps: structure() now; summarize() arrives in M3."""
import json
import logging
import re
import unicodedata

from pydantic import ValidationError

import config
import formulary
import masking
import mock_data
import sarvam_client
from rapidfuzz import fuzz

from schemas import ClinicalRecord, Provenance, Utterance

log = logging.getLogger('vaidya')
PROMPT_VERSION = 'v3'
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
    'language_detected, evidence[{field,quote}]. Evidence has one entry for every non-empty value you output: field '
    'is its path (for example vitals.bp, chief_complaints.0, prescription.1.dose, advice.0, follow_up) and quote is '
    'copied exactly, character for character, from the transcript. Every string value in the JSON, except evidence '
    'quotes and drug names, must be in English even when the transcript is in Marathi or Hindi.'
)

# Hand-written evidence for the two few-shot examples (checked to be verbatim substrings by a test).
EXAMPLE_EVIDENCE = {
    'S1': {'chief_complaints.0': 'doke dukhtay', 'vitals.bp': '150/95 ahe', 'advice.0': 'Salt kami kara',
           'prescription.0.drug': 'Metoprolol', 'prescription.0.dose': '50mg', 'prescription.0.frequency': 'ek goli',
           'prescription.0.timing': 'morning madhe', 'prescription.0.duration': '30 divas',
           'prescription.1.drug': 'Amlodipine', 'prescription.1.dose': '5mg',
           'prescription.1.frequency': 'Amlodipine 5mg raatri jevnanantar', 'prescription.1.timing': 'raatri jevnanantar',
           'follow_up': 'Don aathvadyanni parat ya'},
    'S2': {'chief_complaints.0': 'fever', 'chief_complaints.1': 'breathlessness', 'vitals.temp': '102 fever',
           'vitals.bp': 'BP 90/60', 'vitals.pulse': 'pulse 118'},
}


# Third example: a Marathi (Devanagari) transcript with English output, to stop complaints and advice staying untranslated.
# It shares no text with the eval scenarios (checked by a test).
DEVANAGARI_EXAMPLE = {
    'transcript': 'डॉक्टर, मला पाठदुखी आहे. ताप 99 आहे. हे Diclofenac 50mg दुपारी एक गोळी घ्या, 3 दिवस. गरम पाणी शेका. एका आठवड्यानंतर परत या.',
    'output': {'patient': {'name': '', 'age': '', 'sex': ''}, 'chief_complaints': ['back pain'], 'vitals': {'temp': '99'}, 'diagnosis': '',
               'prescription': [{'drug': 'Diclofenac', 'dose': '50mg', 'frequency': 'once daily', 'timing': 'afternoon', 'duration': '3 days'}],
               'advice': ['apply hot compress'], 'follow_up': '1 week', 'language_detected': 'mr-IN'},
    'evidence': {'chief_complaints.0': 'पाठदुखी', 'vitals.temp': 'ताप 99', 'prescription.0.drug': 'Diclofenac', 'prescription.0.dose': '50mg',
                 'prescription.0.timing': 'दुपारी', 'prescription.0.duration': '3 दिवस', 'advice.0': 'गरम पाणी शेका', 'follow_up': 'एका आठवड्यानंतर परत या'},
}


def _examples():
    out = []
    for sid in ('S1', 'S2'):  # S3 is held out of the prompt so the eval stays honest
        s = mock_data.SCENARIOS[sid]
        rec = ClinicalRecord(**s['record']).model_dump()
        shown = {k: rec[k] for k in SHAPE_KEYS}
        shown['evidence'] = [{'field': f, 'quote': q} for f, q in EXAMPLE_EVIDENCE[sid].items()]
        out.append(f"Example transcript:\n{s['transcript']}\nExample output:\n" + json.dumps(shown, ensure_ascii=False))
    d = DEVANAGARI_EXAMPLE
    shown = {**d['output'], 'evidence': [{'field': f, 'quote': q} for f, q in d['evidence'].items()]}
    out.append(f"Example transcript:\n{d['transcript']}\nExample output:\n" + json.dumps(shown, ensure_ascii=False))
    return '\n\n'.join(out)


ROLE_RULES = (
    '\n\nThe transcript labels each turn with its speaker (Clinician or Patient). Medicines, doses, advice, diagnosis and '
    'follow-up are accepted ONLY from Clinician turns. Symptoms and history come from Patient turns. A medicine that only '
    'the Patient mentions (for example asking about it) must never appear in prescription.'
)


def system_prompt(roles=False):
    return EXTRACTION_PROMPT + (ROLE_RULES if roles else '') + '\n\n' + _examples()


def parse_json(text):
    """Strip reasoning blocks and code fences, then parse the outermost JSON object."""
    text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.S)
    text = re.sub(r'```(?:json)?', '', text)
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < a:
        raise ValueError('no JSON object in model output')
    return json.loads(text[a:b + 1])


def _structure(transcript, roles=False, known_names=()):
    """Returns (record, evidence). Retries once with the error appended, then an empty record + warning."""
    if config.MOCK_MODE:
        return mock_data.scenario_record(mock_data.scenario_for_transcript(transcript)), []
    masker = masking.Masker(known_names) if config.ENABLE_PII_MASKING else None
    sent = masker.mask(transcript) if masker else transcript   # the chat model only ever sees this
    user, err = sent, ''
    for attempt in range(2):
        try:
            raw = sarvam_client.chat(config.LLM_MODEL, system_prompt(roles), user, temperature=0, max_tokens=4096,
                                     reasoning_effort=None)  # extraction needs no thinking; it also ran away on tokens
            data = parse_json(raw)
            if masker:
                data = masker.unmask(data)   # tokens back to the real text; quotes are then checked against the ORIGINAL transcript
            data.pop('red_flags', None)  # red flags come only from the deterministic rules
            evidence = data.pop('evidence', [])
            rec = ClinicalRecord.model_validate(data)
            for rx in rec.prescription:
                rx.drug = formulary.normalize(rx.drug)
            return rec, evidence if isinstance(evidence, list) else []
        except (ValueError, ValidationError) as e:
            err = str(e)[:300]
            log.info('structure attempt %d failed: %s', attempt + 1, err)
            user = f'{sent}\n\nYour previous output was invalid ({err}). Output ONLY the JSON object.'
    return ClinicalRecord(warnings=['Automatic extraction failed. Please fill the form by hand from the transcript.']), []


# ------------------------------------------------ said vs inferred, audit trail (M7)
def _norm(text):
    return ' '.join(unicodedata.normalize('NFC', text or '').translate(str.maketrans('०१२३४५६७८९', '0123456789')).lower().split())


def leaf_fields(rec):
    """(path, value) for every non-empty extracted value."""
    for k, v in rec.patient.model_dump().items():
        yield f'patient.{k}', v
    for i, c in enumerate(rec.chief_complaints):
        yield f'chief_complaints.{i}', c
    for k, v in rec.vitals.model_dump().items():
        yield f'vitals.{k}', v
    yield 'diagnosis', rec.diagnosis
    for i, rx in enumerate(rec.prescription):
        for k, v in rx.model_dump().items():
            yield f'prescription.{i}.{k}', v
    for i, a in enumerate(rec.advice):
        yield f'advice.{i}', a
    yield 'follow_up', rec.follow_up


def literal_quote(value, transcript):
    """The transcript sentence that literally contains the value, or ''. Whitespace and case are ignored."""
    v = _norm(value)
    for sentence in re.split(r'(?<=[.?!।\n])', transcript):
        if v and v in _norm(sentence):
            return sentence.strip()
    return ''


def attach_evidence(rec, evidence, utterances):
    """Fill said / inferred / provenance. A value is `said` only if its quote is a verbatim substring of an utterance
    (checked here by the machine, not trusted from the LLM); everything else is labelled unverified."""
    claimed = {e['field']: e['quote'] for e in evidence if isinstance(e, dict) and isinstance(e.get('field'), str)
               and isinstance(e.get('quote'), str)}
    texts = [(u.id, _norm(u.text)) for u in utterances]
    full = ' '.join(t for _, t in texts)
    transcript = '\n'.join(u.text for u in utterances)
    rec.said, rec.inferred, rec.provenance = [], [], {}
    for path, value in leaf_fields(rec):
        if not value or not str(value).strip():
            continue
        quote = claimed.get(path, '')
        if not quote or _norm(quote) not in full:
            quote = literal_quote(str(value), transcript)
        ids = [i for i, t in texts if quote and _norm(quote) in t]
        if quote and (ids or _norm(quote) in full):
            rec.said.append(f'{path}: {value}')
            rec.provenance[path] = Provenance(source_utterance_ids=ids or [texts[0][0]], model=config.LLM_MODEL,
                                              prompt_version=PROMPT_VERSION, quote=quote, start=full.find(_norm(quote)))
        else:
            rec.inferred.append(f'Unverified, no matching quote - {path}: {value}')
    return rec


def enforce_clinician_orders(rec, utterances):
    """Deterministic guard (F18): a prescribed drug must appear in a Clinician turn, whatever the LLM did."""
    clinician = ' '.join(u.text for u in utterances if u.speaker == 'clinician').lower()
    kept = []
    for rx in rec.prescription:
        if rx.drug and fuzz.partial_ratio(rx.drug.lower(), clinician) >= 85:
            kept.append(rx)
        else:
            rec.warnings.append(f'Removed {rx.drug or "a medicine"}: it was not said by the clinician.')
    rec.prescription = kept


def structure(transcript, utterances=None, known_names=()):
    """Transcript (+ optional diarized turns) -> ClinicalRecord with said/inferred and an audit trail.
    With clinician/patient roles the role-aware prompt is used; without them, the role-free prompt."""
    turns = [u for u in (utterances or []) if u.text.strip()]
    roles = any(u.speaker != 'unknown' for u in turns)
    if roles:
        label = {'clinician': 'Clinician', 'patient': 'Patient', 'unknown': 'Unknown'}
        transcript = '\n'.join(f'{label[u.speaker]}: {u.text}' for u in turns)
    else:
        turns = [Utterance(id='u1', text=transcript)]
    rec, evidence = _structure(transcript, roles, known_names)
    rec.utterances = turns  # also lets /redflags see symptom keywords after edits
    if roles and not rec.warnings:
        enforce_clinician_orders(rec, turns)
    if not any(w.startswith('Automatic extraction failed') for w in rec.warnings):
        attach_evidence(rec, evidence, turns)
    return rec


# ---------------------------------------------------------------- summary (M3)
LANG_NAMES = config.LANGUAGES
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
        return mock_data.SUMMARIES[mock_data.scenario_for_record(record)].get(language) or \
            mock_data.SUMMARIES[mock_data.scenario_for_record(record)]['en-IN'], False
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
        if language in PHRASES and language != 'en-IN':  # the closing safety sentence is fixed, so never leave it in English
            text = re.sub(r'(?is)\s*if you feel worse.*$', '', text).strip()
            if not re.search(r'(?:ख़राब|खराब|तुरंत|लगेच)', text[-60:]):
                text = f"{text} {PHRASES[language]['worse']}"
        problems = check_summary(text, record) if text else ['empty output']
        if not problems:
            return text, False
        log.info('summary attempt %d rejected: %s', attempt + 1, problems)
    return template_summary(record, language if language in PHRASES else 'en-IN'), True


def spoken_language(language, fallback):
    """Language the summary text is actually in: the fixed-phrase template only exists for mr, hi and en, and the
    mock summaries too, so other languages fall back to English (and the English voice)."""
    if language not in PHRASES and (fallback or config.MOCK_MODE):
        return 'en-IN'
    return language
