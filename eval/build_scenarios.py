"""Builds eval/scenarios.jsonl: 32 synthetic consultations (fake patients) for the evaluation harness.
Run: python eval/build_scenarios.py   then review eval/scenarios.jsonl before generating any audio.

Every scenario is held out: none of these texts appear in the extraction prompt's few-shot examples (S1, S2).
Expected values contain only what the script says. Frequency is not scored (it is mostly implied by 'one tablet')."""
import json
from pathlib import Path

L = ('mr', 'hi', 'en')
COMPLAINT = {  # key: (canonical English, mr, hi, en)
    'headache': ('headache', 'डोके दुखतंय', 'सिर में दर्द है', 'a headache'),
    'fever': ('fever', 'ताप आलाय', 'बुखार है', 'fever'),
    'cough': ('cough', 'खोकला आहे', 'खांसी है', 'a cough'),
    'body_pain': ('body pain', 'अंगदुखी आहे', 'बदन दर्द है', 'body pain'),
    'giddiness': ('giddiness', 'चक्कर येतात', 'चक्कर आते हैं', 'giddiness'),
    'abdominal_pain': ('abdominal pain', 'पोटदुखी आहे', 'पेट में दर्द है', 'stomach pain'),
    'tiredness': ('tiredness', 'खूप थकवा आहे', 'बहुत थकान है', 'tiredness'),
    'breathless': ('breathlessness', 'श्वास घ्यायला त्रास होतोय', 'सांस लेने में तकलीफ है', 'shortness of breath'),
    'chest_pain': ('chest pain', 'छातीत दुखतंय', 'सीने में दर्द है', 'chest pain'),
    'vomiting': ('vomiting', 'उलट्या होतायत', 'उल्टी हो रही है', 'vomiting'),
    'loose': ('loose motions', 'जुलाब होतायत', 'दस्त हो रहे हैं', 'loose motions'),
}
TIMING = {
    'morning': ('morning', 'सकाळी', 'सुबह', 'in the morning'),
    'afternoon': ('afternoon', 'दुपारी', 'दोपहर में', 'in the afternoon'),
    'night': ('night, after food', 'रात्री जेवणानंतर', 'रात को खाने के बाद', 'at night after food'),
    'twice': ('morning and evening, after food', 'सकाळी आणि संध्याकाळी जेवणानंतर', 'सुबह और शाम खाने के बाद', 'morning and evening after food'),
}
ADVICE = {
    'low_salt': ('low salt', 'मीठ कमी खा', 'नमक कम खाइए', 'Eat less salt'),
    'sweets': ('avoid sweets', 'गोड खाऊ नका', 'मीठा बंद कीजिए', 'Avoid sweets'),
    'rest': ('rest', 'भरपूर आराम करा', 'खूब आराम कीजिए', 'Take plenty of rest'),
    'water': ('drink plenty of water', 'भरपूर पाणी प्या', 'खूब पानी पीजिए', 'Drink plenty of water'),
    'walk': ('walk daily', 'रोज चाला', 'रोज टहलिए', 'Walk every day'),
}
FOLLOW = {
    '1 week': ('एका आठवड्यानंतर परत या', 'एक हफ्ते बाद दोबारा आइए', 'Come back after one week'),
    '2 weeks': ('दोन आठवड्यांनी परत या', 'दो हफ्ते बाद दोबारा आइए', 'Come back after two weeks'),
    '1 month': ('एका महिन्यानंतर परत या', 'एक महीने बाद दोबारा आइए', 'Come back after one month'),
}
VITAL = {  # key: (label in expected record, mr, hi, en)
    'bp': ('bp', 'बीपी {} आहे', 'बीपी {} है', 'Blood pressure is {}'),
    'temp': ('temp', 'ताप {} आहे', 'बुखार {} है', 'Temperature is {}'),
    'pulse': ('pulse', 'पल्स {} आहे', 'नब्ज़ {} है', 'Pulse is {}'),
    'spo2': ('spo2', 'ऑक्सिजन {} आहे', 'ऑक्सीजन {} है', 'Oxygen saturation is {}'),
    'sugar': ('sugar', 'शुगर {} आहे', 'शुगर {} है', 'Sugar is {}'),
    'resp_rate': ('resp_rate', 'श्वसन दर {} आहे', 'सांस की दर {} है', 'Respiratory rate is {}'),
}
VOICES = {'mr': ('nilesh_mr_conversation', 'ishita_mr_conversational'),   # (clinician, patient), API-verified
          'hi': ('rahul_hi_conversational', 'kavya_hi_conversational'),
          'en': ('ritu_en_medical', 'simran_en_conversation')}
CODE = {'mr': 'mr-IN', 'hi': 'hi-IN', 'en': 'en-IN'}
DAYS = {'mr': 'दिवस', 'hi': 'दिन', 'en': 'days'}


def drug_phrase(lang, drug, dose, timing, days):
    i = L.index(lang)
    t = TIMING[timing][i + 1]
    if lang == 'mr':
        return f'हे {drug} {dose} {t} एक गोळी घ्या, {days} दिवस.'
    if lang == 'hi':
        return f'{drug} {dose} {t} एक गोली लीजिए, {days} दिन.'
    return f'Take {drug} {dose} one tablet {t} for {days} days.'


def build(sid, lang, complaints, vitals, rx, advice=(), follow=None, flags=(), tags=(), title=''):
    i = L.index(lang)
    patient_turn = ' '.join(f'{["डॉक्टर, मला", "डॉक्टर साहब, मुझे", "Doctor, I have"][i]} {COMPLAINT[c][i + 1]}.' for c in complaints[:1])
    patient_turn += ' ' + ' '.join(COMPLAINT[c][i + 1] + '.' for c in complaints[1:])
    vit = ' '.join(VITAL[k][i + 1].format(v) + '.' for k, v in vitals.items())
    rx_text = ' '.join(drug_phrase(lang, d, dose, t, n) for d, dose, t, n in rx)
    adv = ' '.join(ADVICE[a][i + 1] + '.' for a in advice)
    fu = (FOLLOW[follow][i] + '.') if follow else ''
    turns = [{'speaker': 'patient', 'text': patient_turn.strip()}]
    if vit:
        turns.append({'speaker': 'clinician', 'text': vit})
    if rx_text or adv or fu:
        turns.append({'speaker': 'clinician', 'text': ' '.join(x for x in (rx_text, adv, fu) if x)})
    return {
        'id': sid, 'title': title or f'{sid} {lang} ' + ', '.join(complaints), 'language': CODE[lang], 'tags': list(tags),
        'voices': {'clinician': VOICES[lang][0], 'patient': VOICES[lang][1]}, 'turns': turns,
        'expected': {
            'chief_complaints': [COMPLAINT[c][0] for c in complaints], 'vitals': dict(vitals),
            'prescription': [{'drug': d, 'dose': dose, 'timing': TIMING[t][0], 'duration': f'{n} days'} for d, dose, t, n in rx],
            'advice': [ADVICE[a][0] for a in advice], 'follow_up': follow or ''},
        'expected_red_flags': list(flags),
    }


ROWS = [
    # normal visits and multi-drug visits
    ('E01', 'mr', ['headache'], {'bp': '150/95'}, [('Metoprolol', '50mg', 'morning', 30)], ['low_salt'], '2 weeks', (), ()),
    ('E02', 'mr', ['cough'], {'temp': '99'}, [('Cetirizine', '10mg', 'night', 5), ('Paracetamol', '500mg', 'twice', 3)], ['rest'], '1 week', (), ()),
    ('E03', 'mr', ['giddiness'], {'bp': '160/100'}, [('Amlodipine', '5mg', 'morning', 30), ('Telmisartan', '40mg', 'night', 30)], ['low_salt', 'walk'], '1 month', (), ()),
    ('E04', 'mr', ['tiredness'], {'sugar': '210'}, [('Metformin', '500mg', 'twice', 30)], ['sweets', 'walk'], '2 weeks', (), ()),
    ('E05', 'mr', ['body_pain'], {}, [('Paracetamol', '650mg', 'twice', 3), ('Pantoprazole', '40mg', 'morning', 5)], ['rest'], '1 week', (), ()),
    ('E06', 'hi', ['tiredness'], {'sugar': '180'}, [('Metformin', '500mg', 'twice', 30), ('Glimepiride', '1mg', 'morning', 30)], ['sweets', 'walk'], '2 weeks', (), ()),
    ('E07', 'hi', ['headache'], {'bp': '145/92'}, [('Telmisartan', '40mg', 'morning', 30)], ['low_salt'], '1 month', (), ()),
    ('E08', 'hi', ['cough', 'fever'], {'temp': '100'}, [('Azithromycin', '500mg', 'morning', 3), ('Paracetamol', '500mg', 'twice', 3)], ['water', 'rest'], '1 week', (), ()),
    ('E09', 'hi', ['abdominal_pain'], {}, [('Pantoprazole', '40mg', 'morning', 14)], ['water'], '2 weeks', (), ()),
    ('E10', 'hi', ['body_pain'], {}, [('Ibuprofen', '400mg', 'twice', 5)], ['rest'], '1 week', (), ()),
    ('E11', 'en', ['headache'], {'bp': '148/96'}, [('Amlodipine', '5mg', 'morning', 30)], ['low_salt'], '2 weeks', (), ()),
    ('E12', 'en', ['tiredness'], {'sugar': '195'}, [('Metformin', '500mg', 'twice', 30), ('Atorvastatin', '10mg', 'night', 30)], ['sweets', 'walk'], '1 month', (), ()),
    ('E13', 'en', ['cough'], {}, [('Cetirizine', '10mg', 'night', 5), ('Amoxicillin', '500mg', 'twice', 5)], ['water'], '1 week', (), ()),
    ('E14', 'en', ['giddiness'], {'bp': '155/98'}, [('Losartan', '50mg', 'morning', 30)], ['walk'], '2 weeks', (), ()),
    # red-flag cases (expected flags written by hand from the SPEC section 9 table)
    ('R01', 'mr', ['fever', 'breathless'], {'temp': '102', 'bp': '88/58', 'pulse': '122'}, [], [], None, ('RF_SEPSIS', 'RF_HYPOTENSION'), ()),
    ('R02', 'hi', ['fever', 'breathless'], {'temp': '101', 'bp': '96/62', 'pulse': '104', 'resp_rate': '26'}, [], [], None, ('RF_SEPSIS',), ()),
    ('R03', 'en', ['giddiness'], {'bp': '85/55'}, [], [], None, ('RF_HYPOTENSION',), ()),
    ('R04', 'mr', ['headache'], {'bp': '190/115'}, [], [], None, ('RF_HYPERTENSIVE',), ()),
    ('R05', 'hi', ['breathless'], {'spo2': '88', 'pulse': '96'}, [], [], None, ('RF_HYPOXIA',), ()),
    ('R06', 'en', ['fever'], {'temp': '104', 'pulse': '90'}, [], [], None, ('RF_HIGH_FEVER',), ()),
    ('R07', 'mr', ['tiredness'], {'sugar': '340'}, [], [], None, ('RF_HYPERGLYCEMIA',), ()),
    ('R08', 'hi', ['chest_pain'], {'bp': '130/84'}, [], [], None, ('RF_CHEST_PAIN',), ()),
    ('R09', 'en', ['vomiting'], {'pulse': '112', 'bp': '110/70'}, [], [], None, ('RF_DEHYDRATION',), ()),
    ('R10', 'mr', ['loose'], {'pulse': '108'}, [], [], None, ('RF_DEHYDRATION',), ()),
    # noisy and fast-speech variants of earlier scripts (same text, different audio treatment)
    ('N01', 'mr', ['headache'], {'bp': '150/95'}, [('Metoprolol', '50mg', 'morning', 30)], ['low_salt'], '2 weeks', (), ('noisy',)),
    ('N02', 'hi', ['tiredness'], {'sugar': '180'}, [('Metformin', '500mg', 'twice', 30), ('Glimepiride', '1mg', 'morning', 30)], ['sweets', 'walk'], '2 weeks', (), ('noisy',)),
    ('N03', 'en', ['headache'], {'bp': '148/96'}, [('Amlodipine', '5mg', 'morning', 30)], ['low_salt'], '2 weeks', (), ('noisy',)),
    ('N04', 'mr', ['fever', 'breathless'], {'temp': '102', 'bp': '88/58', 'pulse': '122'}, [], [], None, ('RF_SEPSIS', 'RF_HYPOTENSION'), ('noisy',)),
    ('F01', 'mr', ['giddiness'], {'bp': '160/100'}, [('Amlodipine', '5mg', 'morning', 30), ('Telmisartan', '40mg', 'night', 30)], ['low_salt', 'walk'], '1 month', (), ('fast',)),
    ('F02', 'hi', ['cough', 'fever'], {'temp': '100'}, [('Azithromycin', '500mg', 'morning', 3), ('Paracetamol', '500mg', 'twice', 3)], ['water', 'rest'], '1 week', (), ('fast',)),
    ('F03', 'en', ['tiredness'], {'sugar': '195'}, [('Metformin', '500mg', 'twice', 30), ('Atorvastatin', '10mg', 'night', 30)], ['sweets', 'walk'], '1 month', (), ('fast',)),
    ('F04', 'mr', ['headache'], {'bp': '190/115'}, [], [], None, ('RF_HYPERTENSIVE',), ('fast',)),
]

if __name__ == '__main__':
    out = Path(__file__).parent / 'scenarios.jsonl'
    scenarios = [build(sid, lang, c, v, rx, a, f, fl, tg) for sid, lang, c, v, rx, a, f, fl, tg in ROWS]
    out.write_text('\n'.join(json.dumps(s, ensure_ascii=False) for s in scenarios) + '\n', encoding='utf-8')
    print(f'wrote {len(scenarios)} scenarios to {out}')
