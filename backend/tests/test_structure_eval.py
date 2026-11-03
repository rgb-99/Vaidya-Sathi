"""Live eval of structure() on demo transcripts. Opt-in: RUN_LIVE=1 pytest tests/test_structure_eval.py -s
(needs a real key, makes ~4 chat calls). Also runnable directly: python tests/test_structure_eval.py"""
import os
import sys
from pathlib import Path

import pytest
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import config
import llm

T = lambda n: (ROOT / 'demo' / 'transcripts' / f'{n}.txt').read_text(encoding='utf-8').strip()

# Expected facts = only what each text actually says. Exact = normalized equality; fuzzy = token_set_ratio >= 60.
S2_WORDS = 'पेशंटला एकशे दोन ताप आहे श्वास घ्यायला त्रास होतोय बीपी नव्वद बाय साठ खाली आला आहे पल्स एकशे अठरा'
CASES = {
    'S1': (T('S1'), {
        'vitals.bp': '150/95', 'follow_up~': '2 weeks', 'advice~': ['low salt'],
        'rx': [('Metoprolol', '50mg', 'morning', '30 days'), ('Amlodipine', '5mg', 'night after dinner', '')]}),
    'S2': (T('S2'), {
        'vitals.temp': '102', 'vitals.bp': '90/60', 'vitals.pulse': '118', 'complaints~': ['fever', 'breathlessness'], 'rx': []}),
    'S2-words': (S2_WORDS, {
        'vitals.temp': '102', 'vitals.bp': '90/60', 'vitals.pulse': '118', 'complaints~': ['fever', 'breathlessness'], 'rx': []}),
    'S3': (T('S3'), {
        'vitals.sugar': '180', 'follow_up~': '2 weeks', 'advice~': ['avoid sweets', 'walk daily'],
        'rx': [('Metformin', '500mg', 'morning and evening after meals', '')]}),
}


def norm(s):
    return ''.join(str(s).lower().split())


def fuzzy(got, want):
    return any(fuzz.token_set_ratio(want.lower(), g.lower()) >= 60 for g in got)


def score(rec, exp):
    ok = total = 0
    wrong, invented = [], []
    vit = rec.vitals.model_dump()
    for k, want in exp.items():
        if k.startswith('vitals.'):
            total += 1
            good = norm(vit[k.split('.')[1]]) == norm(want)
            ok += good
            if not good:
                wrong.append((k, want, vit[k.split('.')[1]]))
        elif k == 'follow_up~':
            total += 1
            good = fuzzy([rec.follow_up], want)
            ok += good
            if not good:
                wrong.append((k, want, rec.follow_up))
        elif k in ('advice~', 'complaints~'):
            got = rec.advice if k == 'advice~' else rec.chief_complaints
            for w in want:
                total += 1
                good = fuzzy(got, w)
                ok += good
                if not good:
                    wrong.append((k, w, got))
    by_drug = {r.drug.lower(): r for r in rec.prescription}
    for drug, dose, timing, dur in exp['rx']:
        r = by_drug.get(drug.lower())
        total += 1
        ok += bool(r)
        if not r:
            wrong.append(('rx.drug', drug, list(by_drug)))
            total += 1 + bool(timing) + bool(dur)
            continue
        total += 1
        good = norm(r.dose) == norm(dose)
        ok += good
        if not good:
            wrong.append((f'rx.{drug}.dose', dose, r.dose))
        for field, want in (('timing', timing), ('duration', dur)):
            if want:
                total += 1
                good = fuzzy([getattr(r, field)], want)
                ok += good
                if not good:
                    wrong.append((f'rx.{drug}.{field}', want, getattr(r, field)))
    known = {d.lower() for d, *_ in exp['rx']}
    invented = [r.drug for r in rec.prescription if r.drug.lower() not in known]
    return ok, total, wrong, invented


def run():
    config.MOCK_MODE = False
    ok_all = tot_all = 0
    all_invented = []
    for name, (text, exp) in CASES.items():
        rec = llm.structure(text)
        ok, total, wrong, invented = score(rec, exp)
        ok_all, tot_all = ok_all + ok, tot_all + total
        all_invented += invented
        print(f'{name}: {ok}/{total} fields correct; invented drugs: {invented or "none"}; warnings: {rec.warnings or "none"}')
        for w in wrong:
            print('   wrong:', w)
    print(f'TOTAL {ok_all}/{tot_all} = {100 * ok_all / tot_all:.0f}%')
    return ok_all / tot_all, all_invented


@pytest.mark.skipif(not os.getenv('RUN_LIVE'), reason='live eval: set RUN_LIVE=1')
def test_structure_accuracy_and_no_invented_drugs():
    acc, invented = run()
    assert invented == [] and acc >= 0.9


if __name__ == '__main__':
    run()
