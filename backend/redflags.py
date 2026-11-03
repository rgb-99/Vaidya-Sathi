"""Deterministic red-flag rules (SPEC TRD section 9). Pure Python: no network, no LLM.
Demo-grade screening rules; a clinician must review them before any real use (docs/SAFETY.md)."""
import re

from schemas import ClinicalRecord, RedFlag

_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

KEYWORDS = {
    'breathlessness': ['breathless', 'shortness of breath', 'short of breath', 'difficulty breathing', 'trouble breathing',
                       'dam lagna', 'dam lagto', 'dhap lagte', 'dhap lagtay', 'shwas', 'श्वास', 'सांस', 'दम लागणे', 'दम लागतो', 'धाप'],
    'chest pain': ['chest pain', 'chhati dukhna', 'chhati me dard', 'chhatit dukhtay', 'chhatit dukhte', 'seene me dard',
                   'छाती दुख', 'छातीत दुख', 'छाती में दर्द', 'सीने में दर्द'],
    'vomiting': ['vomiting', 'vomit', 'ulti', 'उलटी', 'उल्टी', 'ओकारी'],
    'loose motions': ['loose motion', 'diarrhea', 'diarrhoea', 'dast', 'julab', 'दस्त', 'जुलाब'],
}

TITLES = {
    'RF_SEPSIS': 'Possible sepsis', 'RF_HYPOTENSION': 'Very low blood pressure', 'RF_HYPERTENSIVE': 'Severely high blood pressure',
    'RF_HYPOXIA': 'Low oxygen level', 'RF_HIGH_FEVER': 'Very high fever', 'RF_HYPERGLYCEMIA': 'Very high blood sugar',
    'RF_CHEST_PAIN': 'Chest pain reported', 'RF_DEHYDRATION': 'Possible dehydration',
}
ACTIONS = {
    'RF_SEPSIS': 'Possible sepsis. Refer urgently and inform the doctor.',
    'RF_HYPOTENSION': 'Very low blood pressure. Escalate immediately.',
    'RF_HYPERTENSIVE': 'Severely high blood pressure. Escalate to doctor now.',
    'RF_HYPOXIA': 'Low oxygen level. Escalate immediately.',
    'RF_HIGH_FEVER': 'Very high fever. Inform the doctor.',
    'RF_HYPERGLYCEMIA': 'Very high blood sugar. Inform the doctor.',
    'RF_CHEST_PAIN': 'Chest pain reported. Escalate immediately.',
    'RF_DEHYDRATION': 'Possible dehydration. Inform the doctor.',
}
# Spoken alert text (SPEC 8.4): fixed strings, no LLM, never a dose. Marathi and Hindi are unreviewed drafts.
ALERTS = {
    'RF_SEPSIS': {'en-IN': 'Warning. Signs of possible serious infection. Refer the patient to the hospital urgently and inform the doctor.',
                  'hi-IN': 'सावधान। गंभीर संक्रमण की संभावना। मरीज़ को तुरंत अस्पताल भेजें और डॉक्टर को सूचित करें।',
                  'mr-IN': 'सावधान. गंभीर संसर्गाची शक्यता. रुग्णाला तातडीने रुग्णालयात पाठवा आणि डॉक्टरांना कळवा.'},
    'RF_HYPOTENSION': {'en-IN': 'Warning. Very low blood pressure. Escalate immediately.',
                       'hi-IN': 'सावधान। रक्तचाप बहुत कम है। तुरंत डॉक्टर को बुलाएं।',
                       'mr-IN': 'सावधान. रक्तदाब खूप कमी आहे. तातडीने डॉक्टरांना कळवा.'},
    'RF_HYPERTENSIVE': {'en-IN': 'Warning. Severely high blood pressure. Inform the doctor now.',
                        'hi-IN': 'सावधान। रक्तचाप बहुत ज़्यादा है। अभी डॉक्टर को बताएं।',
                        'mr-IN': 'सावधान. रक्तदाब खूप जास्त आहे. आत्ताच डॉक्टरांना कळवा.'},
    'RF_HYPOXIA': {'en-IN': 'Warning. Low oxygen level. Escalate immediately.',
                   'hi-IN': 'सावधान। ऑक्सीजन का स्तर कम है। तुरंत डॉक्टर को बुलाएं।',
                   'mr-IN': 'सावधान. ऑक्सिजनची पातळी कमी आहे. तातडीने डॉक्टरांना कळवा.'},
    'RF_HIGH_FEVER': {'en-IN': 'Very high fever. Inform the doctor.',
                      'hi-IN': 'बहुत तेज़ बुखार है। डॉक्टर को बताएं।',
                      'mr-IN': 'खूप जास्त ताप आहे. डॉक्टरांना कळवा.'},
    'RF_HYPERGLYCEMIA': {'en-IN': 'Very high blood sugar. Inform the doctor.',
                         'hi-IN': 'ब्लड शुगर बहुत ज़्यादा है। डॉक्टर को बताएं।',
                         'mr-IN': 'रक्तातील साखर खूप जास्त आहे. डॉक्टरांना कळवा.'},
    'RF_CHEST_PAIN': {'en-IN': 'Warning. Chest pain reported. Escalate immediately.',
                      'hi-IN': 'सावधान। सीने में दर्द की शिकायत है। तुरंत डॉक्टर को बुलाएं।',
                      'mr-IN': 'सावधान. छातीत दुखत असल्याचे सांगितले आहे. तातडीने डॉक्टरांना कळवा.'},
    'RF_DEHYDRATION': {'en-IN': 'Possible dehydration. Inform the doctor.',
                       'hi-IN': 'शरीर में पानी की कमी हो सकती है। डॉक्टर को बताएं।',
                       'mr-IN': 'शरीरात पाण्याची कमतरता असू शकते. डॉक्टरांना कळवा.'},
}


def parse_number(s):
    """First number in a string ('102', '102F', '102 degree', '98.6', '१०२'); None if there is none."""
    m = re.search(r'\d+(?:\.\d+)?', (s or '').translate(_DIGITS))
    return float(m.group()) if m else None


def parse_bp(s):
    """'90/60' -> (90, 60); also '90 / 60', 'BP 90/60'. None when not a systolic/diastolic pair."""
    m = re.search(r'(\d{2,3})\s*[/\\]\s*(\d{2,3})', (s or '').translate(_DIGITS))
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_temp_f(s):
    """Temperature in Fahrenheit. The record stores degrees F as said; values under 45 are read as Celsius."""
    v = parse_number(s)
    if v is None:
        return None
    return v * 9 / 5 + 32 if v < 45 else v


def _matches(kw, low):
    if not kw.isascii():  # Devanagari: plain substring
        return kw in low
    # Latin: must start at a word boundary; short words (ulti, dast) must also end on one.
    return re.search(r'\b' + re.escape(kw) + (r'\b' if len(kw) <= 5 else ''), low) is not None


def has_keyword(kind, text):
    low = (text or '').lower()
    return any(_matches(k, low) for k in KEYWORDS[kind])


def _fmt(v):
    return f'{v:g}'


def check(record: ClinicalRecord, transcript: str = '') -> list[RedFlag]:
    """Evaluate every rule. Missing inputs never trigger a rule. Symptoms come from the complaints plus the
    transcript (passed in, or stored as record.utterances by /api/structure)."""
    text = ' '.join(record.chief_complaints + [u.text for u in record.utterances] + [transcript])
    v = record.vitals
    temp, bp, pulse = parse_temp_f(v.temp), parse_bp(v.bp), parse_number(v.pulse)
    spo2, rr, sugar = parse_number(v.spo2), parse_number(v.resp_rate), parse_number(v.sugar)
    sbp, dbp = (bp if bp else (None, None))
    breath = has_keyword('breathlessness', text)
    flags = []

    def add(rule_id, severity, inputs):
        flags.append(RedFlag(rule_id=rule_id, title=TITLES[rule_id], severity=severity,
                             matched_inputs=inputs, action_text=ACTIONS[rule_id]))

    t_in, bp_in, p_in = (f'temp {_fmt(temp)}F' if temp is not None else ''), (f'BP {sbp}/{dbp}' if bp else ''), \
        (f'pulse {_fmt(pulse)}' if pulse is not None else '')

    if temp is not None and temp >= 100.4:
        circ = [x for x, ok in ((bp_in, sbp is not None and sbp < 100), (p_in, pulse is not None and pulse > 100)) if ok]
        resp = [x for x, ok in (('breathlessness keyword', breath), (f'resp rate {rr and _fmt(rr)}', rr is not None and rr > 22)) if ok]
        if circ and resp:
            add('RF_SEPSIS', 'urgent', [t_in] + circ + resp)
    if sbp is not None and sbp <= 90:  # spec table says < 90 but S2 (90/60) must trigger: see DECISIONS.md
        add('RF_HYPOTENSION', 'urgent', [bp_in])
    if bp and (sbp >= 180 or dbp >= 120):
        add('RF_HYPERTENSIVE', 'urgent', [bp_in])
    if spo2 is not None and spo2 < 92:
        add('RF_HYPOXIA', 'urgent', [f'SpO2 {_fmt(spo2)}'])
    if temp is not None and temp >= 103:
        add('RF_HIGH_FEVER', 'warning', [t_in])
    if sugar is not None and sugar > 300:
        add('RF_HYPERGLYCEMIA', 'warning', [f'sugar {_fmt(sugar)}'])
    if has_keyword('chest pain', text):
        add('RF_CHEST_PAIN', 'urgent', ['chest pain keyword'])
    gi = [x for x, ok in (('vomiting keyword', has_keyword('vomiting', text)), ('loose motions keyword', has_keyword('loose motions', text))) if ok]
    if gi:
        circ = [x for x, ok in ((p_in, pulse is not None and pulse > 100), (bp_in, sbp is not None and sbp < 100)) if ok]
        if circ:
            add('RF_DEHYDRATION', 'warning', gi + circ)
    return flags


def alert_text(flags, language):
    """Fixed spoken text for the given flags in the language (English fallback). No LLM, no doses."""
    lang = language if language in ('mr-IN', 'hi-IN', 'en-IN') else 'en-IN'
    return ' '.join(ALERTS[f.rule_id][lang] for f in flags if f.rule_id in ALERTS)
