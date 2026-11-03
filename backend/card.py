"""Print-friendly prescription card (large text, morning/afternoon/night grid) for elderly patients."""
from html import escape

COLUMNS = [('morning', 'Morning'), ('afternoon', 'Afternoon'), ('night', 'Evening / Night')]
_WORDS = {'morning': ('morning',), 'afternoon': ('afternoon', 'noon'), 'night': ('night', 'evening', 'bedtime', 'dinner')}


def slots(record):
    """Place each medicine in the columns the clinician's own words name. Nothing is inferred: 'twice daily'
    without a time of day goes to `other` ("as directed")."""
    grid = {k: [] for k, _ in COLUMNS}
    other = []
    for rx in record.prescription:
        if not rx.drug.strip():
            continue
        said = f'{rx.frequency} {rx.timing}'.lower()
        hits = [k for k, words in _WORDS.items() if any(w in said for w in words)]
        label = ' '.join(x for x in (rx.drug, rx.dose) if x)
        detail = ', '.join(x for x in (rx.timing, rx.duration and f'for {rx.duration}') if x)
        for k in hits:
            grid[k].append((label, detail))
        if not hits:
            other.append((label, ', '.join(x for x in (rx.frequency, rx.timing, rx.duration and f'for {rx.duration}') if x)))
    return grid, other


def render_card(record):
    grid, other = slots(record)
    e = escape
    cell = lambda items: ''.join(f'<div class="med"><b>{e(a)}</b><br><span>{e(b)}</span></div>' for a, b in items) or '&mdash;'
    head = ''.join(f'<th>{e(label)}</th>' for _, label in COLUMNS)
    body = ''.join(f'<td>{cell(grid[k])}</td>' for k, _ in COLUMNS)
    extra = f'<h2>As directed</h2>{cell(other)}' if other else ''
    advice = ''.join(f'<li>{e(a)}</li>' for a in record.advice)
    name = e(record.patient.name) or 'Patient'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Medicine card</title>
<style>
body{{font:28px/1.4 system-ui,sans-serif;margin:24px;color:#000}} h1{{font-size:40px;margin:0 0 8px}} h2{{font-size:30px}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}} th,td{{border:3px solid #000;padding:12px;vertical-align:top;font-size:28px}}
th{{background:#eee}} .med{{margin-bottom:12px}} .med span{{font-size:22px}} .note{{font-size:18px;margin-top:24px;border-top:2px solid #000;padding-top:8px}}
</style></head><body>
<h1>{name}: your medicines</h1>
<table><tr>{head}</tr><tr>{body}</tr></table>{extra}
{f'<h2>Advice</h2><ul>{advice}</ul>' if advice else ''}
{f'<h2>Come back</h2><p>{e(record.follow_up)}</p>' if record.follow_up else ''}
<p><b>If you feel worse, go to the hospital immediately.</b></p>
<p class="note">AI-assisted documentation. Clinician must review. Not a substitute for medical judgement. Demo data only.</p>
</body></html>'''
