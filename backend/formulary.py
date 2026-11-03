"""Common drug names for fuzzy-matching STT/LLM output (TRD 7.4). Demo list, not a clinical reference."""
from rapidfuzz import fuzz, process

DRUGS = [
    'Metoprolol', 'Amlodipine', 'Metformin', 'Paracetamol', 'Atorvastatin', 'Telmisartan', 'Pantoprazole',
    'Azithromycin', 'Amoxicillin', 'Cetirizine', 'ORS', 'Glimepiride', 'Losartan', 'Aspirin', 'Ondansetron',
    'Atenolol', 'Rosuvastatin', 'Omeprazole', 'Ranitidine', 'Ibuprofen', 'Diclofenac', 'Ciprofloxacin',
    'Doxycycline', 'Levocetirizine', 'Montelukast', 'Salbutamol', 'Prednisolone', 'Furosemide', 'Enalapril',
    'Ramipril', 'Clopidogrel', 'Insulin', 'Gliclazide', 'Sitagliptin', 'Vildagliptin', 'Levothyroxine',
    'Folic acid', 'Iron', 'Calcium', 'Vitamin D3',
]
CUTOFF = 85
_LOWER = {d.lower(): d for d in DRUGS}


def normalize(name):
    """Closest formulary name at score >= 85, otherwise the input unchanged."""
    if not name or not name.strip():
        return name
    m = process.extractOne(name.strip().lower(), list(_LOWER), scorer=fuzz.ratio, score_cutoff=CUTOFF)
    return _LOWER[m[0]] if m else name


def key_terms():
    return list(DRUGS)
