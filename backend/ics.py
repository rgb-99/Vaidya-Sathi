"""Reminder calendar file (.ics) from a signed prescription. Times are floating local times."""
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import card

SLOT_TIMES = {'morning': '080000', 'afternoon': '140000', 'night': '200000'}
SLOT_NAMES = {'morning': 'morning', 'afternoon': 'afternoon', 'night': 'evening/night'}
OTHER_TIME = '090000'


def esc(text):
    return re.sub(r'([\;,])', r'\\\1', text).replace('\n', '\\n')


def fold(line):
    """RFC 5545 line folding: at most 75 octets per line, continuation lines start with a space."""
    out, raw = [], line.encode('utf-8')
    while len(raw) > 75:
        cut = 75
        while raw[cut] & 0xC0 == 0x80:   # do not split a multi-byte character
            cut -= 1
        out.append(raw[:cut].decode('utf-8'))
        raw = b' ' + raw[cut:]
    out.append(raw.decode('utf-8'))
    return '\r\n'.join(out)


def days_from(duration):
    """Number of days named by '30 days' / '2 weeks' / '1 month'; None when the clinician gave none."""
    m = re.search(r'(\d+)\s*(day|week|month)', (duration or '').lower())
    return int(m.group(1)) * {'day': 1, 'week': 7, 'month': 30}[m.group(2)] if m else None


def build(record, start=None, now=None):
    start = start or date.today()
    stamp = (now or datetime.now(timezone.utc)).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Vaidya Saathi//Medicine reminders//EN', 'CALSCALE:GREGORIAN']
    grid, other = card.slots(record)
    by_drug = {rx.drug: rx for rx in record.prescription}

    def add(label, when, drug, note):
        days = days_from(by_drug[drug].duration) if drug in by_drug else None
        lines.extend(['BEGIN:VEVENT', f'UID:{uuid.uuid4()}@vaidya-saathi', f'DTSTAMP:{stamp}',
                      f'DTSTART:{start.strftime("%Y%m%d")}T{when}', 'DURATION:PT15M',
                      f'SUMMARY:{esc("Take " + label)}', f'DESCRIPTION:{esc(note)}'])
        if days:
            lines.append(f'RRULE:FREQ=DAILY;COUNT={days}')
        lines.extend(['BEGIN:VALARM', 'ACTION:DISPLAY', f'DESCRIPTION:{esc("Take " + label)}', 'TRIGGER:PT0M', 'END:VALARM', 'END:VEVENT'])

    for slot, items in grid.items():
        for label, detail in items:
            add(label, SLOT_TIMES[slot], label.split(' ')[0], f'{detail}. Medicine reminder from your clinician.' if detail else 'Medicine reminder from your clinician.')
    for label, detail in other:
        add(label, OTHER_TIME, label.split(' ')[0], f'{detail}. Time of day was not stated, please follow your doctor.')
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold(l) for l in lines) + '\r\n'
