"""PII masking before text reaches the chat model (F28). Names, phone numbers and long digit strings become tokens
like <NAME_1>; the map lives only in memory for one request; tokens are restored in the model's output.

Limits (honest): names are found by cue words ("my name is X", "Mr./Mrs./Smt./Shri X", "नाव X", "नाम X") and by
names the caller already knows. A name said with no cue word cannot be detected without a name-recognition model.
Clinical numbers (BP 150/95, pulse 118, doses) are not touched: only digit runs of 9+ digits are."""
import re

# Latin and Devanagari letters make up a name word.
_W = r'[A-Z][a-z]+|[ऀ-ॣ०-ॿ]{2,}'   # Devanagari letters; the danda (U+0964) is punctuation
_NAME = rf'(?:{_W})(?:\s+(?:{_W})){{0,2}}'
NAME_CUES = [
    rf'(?i:my name is|i am|i\'m|name is|naam|nav)\s+(?P<n1>{_NAME})',
    rf'\b(?:Mr|Mrs|Ms|Miss|Smt|Shri|Sri|Dr)\.?\s+(?P<n2>{_NAME})',
    rf'(?:माझे नाव|माझं नाव|नाव|मेरा नाम|नाम|श्रीमती|श्री|सौ\.?)\s+(?P<n3>{_NAME})',
]
# +91 / 0 prefix optional, 10 digits starting 6-9, optional single separators.
PHONE = re.compile(r'(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)')
# Any run of 9+ digits (allowing spaces or hyphens between groups): Aadhaar, ABHA, MRN, account numbers.
LONG_DIGITS = re.compile(r'(?<!\d)\d(?:[\s-]?\d){8,}(?!\d)')
# Words that follow a cue but are not names ("I am fine", "name is not...").
STOP = {'fine', 'ok', 'okay', 'not', 'here', 'having', 'taking', 'feeling', 'sick', 'going', 'coming', 'doctor', 'and', 'आहे', 'आहेत',
        'है', 'हैं', 'हूँ', 'हूं', 'नाही', 'नहीं', 'आणि', 'और', 'का', 'की', 'को', 'ला', 'ने', 'मला', 'मुझे'}


class Masker:
    def __init__(self, known_names=()):
        self.map = {}          # token -> original text
        self._by_text = {}
        self._known = [n for n in known_names if n and n.strip()]

    def _token(self, kind, original):
        key = ' '.join(original.lower().split())   # 'Anita Rao' and 'ANITA RAO' are the same person
        if key in self._by_text:
            return self._by_text[key]
        n = sum(t.startswith(f'<{kind}_') for t in self.map) + 1
        token = f'<{kind}_{n}>'
        self.map[token], self._by_text[key] = original, token
        return token

    def mask(self, text):
        text = text or ''
        for name in sorted(self._known, key=len, reverse=True):   # names the caller already knows
            text = re.sub(re.escape(name), lambda m: self._token('NAME', m.group()), text, flags=re.I)
        text = PHONE.sub(lambda m: self._token('PHONE', m.group()), text)
        text = LONG_DIGITS.sub(lambda m: self._token('ID', m.group()), text)
        for pattern in NAME_CUES:
            def sub(m):
                group = next(g for g in ('n1', 'n2', 'n3') if m.groupdict().get(g))
                words = m.group(group).split()
                while words and words[-1].lower() in STOP:   # 'सुनीता देशमुख है' -> the name is 'सुनीता देशमुख'
                    words.pop()
                if not words or words[0].lower() in STOP:
                    return m.group()
                name = ' '.join(words)
                cut = m.start(group) - m.start()
                return m.group()[:cut] + self._token('NAME', name) + m.group()[cut + len(name):]
            text = re.sub(pattern, sub, text)
        return text

    def unmask(self, value):
        """Restore tokens in a string, or in every string inside a dict or list."""
        if isinstance(value, str):
            for token, original in self.map.items():
                value = value.replace(token, original)
            return value
        if isinstance(value, list):
            return [self.unmask(v) for v in value]
        if isinstance(value, dict):
            return {k: self.unmask(v) for k, v in value.items()}
        return value
