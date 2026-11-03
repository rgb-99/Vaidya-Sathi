"""Canned data for MOCK_MODE. All patients and conversations are fake."""
from schemas import ClinicalRecord, RedFlag

SCENARIOS = {
    'S1': {
        'title': 'S1: OPD hypertension (Marathi-Hindi-English)',
        'language': 'mr-IN',
        'transcript': (
            'Doctor: Namaskar, kasa ahe? Kay tras hotoy? '
            'Patient: Doctor, doke dukhtay, don teen divas pasun. '
            'Doctor: BP check kela, 150/95 ahe, thoda high ahe. Salt kami kara. '
            'He Metoprolol 50mg morning madhe ek goli ghet ja, 30 divas. '
            'Ani Amlodipine 5mg raatri jevnanantar. Don aathvadyanni parat ya.'
        ),
        'record': {
            'patient': {'name': '', 'age': '', 'sex': ''},
            'chief_complaints': ['headache'],
            'vitals': {'bp': '150/95'},
            'diagnosis': '',
            'prescription': [
                {'drug': 'Metoprolol', 'dose': '50mg', 'frequency': 'once daily',
                 'timing': 'morning', 'duration': '30 days'},
                {'drug': 'Amlodipine', 'dose': '5mg', 'frequency': 'once daily',
                 'timing': 'night, after dinner', 'duration': ''},
            ],
            'advice': ['Eat less salt'],
            'follow_up': '2 weeks',
            'language_detected': 'mr-IN',
        },
        'red_flags': [],
    },
    'S2': {
        'title': 'S2: Rural PHC emergency (red-flag)',
        'language': 'mr-IN',
        'transcript': (
            'Nurse: Patient la 102 fever ahe, breathlessness pan vattoy, '
            'BP 90/60 drop zala ahe, pulse 118.'
        ),
        'record': {
            'patient': {'name': '', 'age': '', 'sex': ''},
            'chief_complaints': ['fever', 'breathlessness'],
            'vitals': {'bp': '90/60', 'temp': '102', 'pulse': '118'},
            'language_detected': 'mr-IN',
        },
        'red_flags': [
            {'rule_id': 'RF_SEPSIS', 'title': 'Possible sepsis', 'severity': 'urgent',
             'matched_inputs': ['temp 102F', 'BP 90/60', 'pulse 118', 'breathlessness keyword'],
             'action_text': 'Possible sepsis. Refer urgently and inform the doctor.'},
            {'rule_id': 'RF_HYPOTENSION', 'title': 'Very low blood pressure', 'severity': 'urgent',
             'matched_inputs': ['BP 90/60'],
             'action_text': 'Very low blood pressure. Escalate immediately.'},
        ],
    },
    'S3': {
        'title': 'S3: Diabetes follow-up (Hindi-heavy)',
        'language': 'hi-IN',
        'transcript': (
            'Doctor: Namaste, sugar kaisi hai? '
            'Patient: Doctor sahab, thoda thakan rehti hai. '
            'Doctor: Aaj fasting sugar 180 aayi hai. Metformin 500mg subah aur shaam, khana khane ke baad lena. '
            'Meetha band kijiye aur roz tehliye. Do hafte baad dobara aaiye.'
        ),
        'record': {
            'patient': {'name': '', 'age': '', 'sex': ''},
            'chief_complaints': ['tiredness'],
            'vitals': {'sugar': '180'},
            'diagnosis': '',
            'prescription': [
                {'drug': 'Metformin', 'dose': '500mg', 'frequency': 'twice daily',
                 'timing': 'morning and evening, after meals', 'duration': ''},
            ],
            'advice': ['Avoid sweets', 'Walk daily'],
            'follow_up': '2 weeks',
            'language_detected': 'hi-IN',
        },
        'red_flags': [],
    },
}

DEFAULT_SCENARIO = 'S1'

SUMMARIES = {
    'S1': {
        'mr-IN': 'तुमचा रक्तदाब थोडा जास्त आहे. सकाळी: मेटोप्रोलॉल ५० मिलिग्रॅमची एक गोळी. रात्री जेवणानंतर: अम्लोडिपिन ५ मिलिग्रॅमची एक गोळी. मीठ कमी खा. दोन आठवड्यांनी परत या. बरे वाटत नसेल तर लगेच दवाखान्यात जा.',
        'hi-IN': 'आपका ब्लड प्रेशर थोड़ा ज़्यादा है। सुबह: मेटोप्रोलोल 50 मिलीग्राम की एक गोली। रात को खाने के बाद: एम्लोडिपिन 5 मिलीग्राम की एक गोली। नमक कम खाइए। दो हफ्ते बाद फिर आइए। तबीयत ख़राब लगे तो तुरंत अस्पताल जाइए।',
        'en-IN': 'Your blood pressure is a little high. Morning: one Metoprolol 50 mg tablet. Night after dinner: one Amlodipine 5 mg tablet. Eat less salt. Come back in two weeks. If you feel worse, go to the hospital immediately.',
    },
    'S2': {
        'mr-IN': 'डॉक्टरांनी सांगितलेली कोणतीही औषधे नोंदवलेली नाहीत. बरे वाटत नसेल तर लगेच दवाखान्यात जा.',
        'hi-IN': 'डॉक्टर द्वारा कोई दवा दर्ज नहीं की गई है। तबीयत ख़राब लगे तो तुरंत अस्पताल जाइए।',
        'en-IN': 'No medicines were recorded by the doctor. If you feel worse, go to the hospital immediately.',
    },
    'S3': {
        'mr-IN': 'तुमची साखर थोडी जास्त आहे. सकाळी आणि संध्याकाळी जेवणानंतर: मेटफॉर्मिन ५०० मिलिग्रॅमची एक गोळी. गोड खाऊ नका आणि रोज चाला. दोन आठवड्यांनी परत या. बरे वाटत नसेल तर लगेच दवाखान्यात जा.',
        'hi-IN': 'आपकी शुगर थोड़ी ज़्यादा है। सुबह और शाम खाने के बाद: मेटफॉर्मिन 500 मिलीग्राम की एक गोली। मीठा बंद कीजिए और रोज़ टहलिए। दो हफ्ते बाद फिर आइए। तबीयत ख़राब लगे तो तुरंत अस्पताल जाइए।',
        'en-IN': 'Your sugar is a little high. Morning and evening after meals: one Metformin 500 mg tablet. Avoid sweets and walk daily. Come back in two weeks. If you feel worse, go to the hospital immediately.',
    },
}

def scenario_record(sid):
    s = SCENARIOS[sid]
    return ClinicalRecord(**s['record'], red_flags=[RedFlag(**f) for f in s['red_flags']])


def scenario_for_transcript(text):
    """Best-effort match of a transcript back to a scenario; S1 by default."""
    for sid, s in SCENARIOS.items():
        if text and text.strip() == s['transcript'].strip():
            return sid
    return DEFAULT_SCENARIO


def scenario_for_record(record):
    """Match a (possibly edited) record to a scenario by its first drug; S2 has none."""
    first = record.prescription[0].drug.lower() if record.prescription else ''
    for sid, s in SCENARIOS.items():
        rx = s['record'].get('prescription') or [{}]
        if rx[0].get('drug', '').lower() == first:
            return sid
    return DEFAULT_SCENARIO


def scenario_for_filename(filename):
    name = (filename or '').upper()
    for sid in SCENARIOS:
        if sid in name:
            return sid
    return DEFAULT_SCENARIO
