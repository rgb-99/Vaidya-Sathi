"""Run the full pipeline on the synthetic scenarios and report measured metrics.
  python eval/run_eval.py --all                 # text mode: scenario scripts go straight to structure() (LLM calls only)
  python eval/run_eval.py --all --mode audio    # needs eval/audio/*.wav from eval/synthesize_audio.py; adds STT
  options: --only E01,R01  --workers 4  --diarize  --keyterms  --keyterms-ab  --no-latest
Exit status is 1 when the regression gate fails (any hallucination, or a headline metric down by more than 2 points)."""
import argparse
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'eval'))

from rapidfuzz import fuzz

import config
import llm
import redflags
import report
import synthesize_audio
import voice

SYNONYMS = {'breathlessness': ['shortness of breath', 'difficulty breathing', 'breathless', 'trouble breathing'],
            'giddiness': ['dizziness', 'dizzy', 'vertigo', 'light-headed'],
            'abdominal pain': ['stomach pain', 'stomach ache', 'abdominal pain'], 'body pain': ['body ache', 'bodyache', 'body pain'],
            'loose motions': ['diarrhea', 'diarrhoea', 'loose stools', 'loose motion'], 'tiredness': ['fatigue', 'weakness', 'tired']}
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
# Advice is paraphrased by the model ("Eat less salt" for "low salt"), so it is matched on a key word.
ADVICE_KEYWORDS = {'low salt': 'salt', 'avoid sweets': 'sweet', 'walk daily': 'walk', 'rest': 'rest', 'drink plenty of water': 'water'}
GROUPS = ['complaints', 'vitals', 'drug', 'dose', 'timing', 'duration', 'advice', 'follow_up']


def compact(s):
    return ''.join(str(s).lower().split())


def period(s):
    """('30', 'day') from '30 days', 'for 2 weeks', 'one month'; None if unreadable."""
    s = str(s).lower()
    n = re.search(r'\d+', s)
    num = n.group() if n else next((str(v) for w, v in WORDS.items() if re.search(rf'\b{w}\b', s)), None)
    unit = re.search(r'(day|week|month)', s)
    return (num, unit.group()) if num and unit else None


def same(group, want, got):
    if group == 'advice' and want.lower() in ADVICE_KEYWORDS:
        return ADVICE_KEYWORDS[want.lower()] in got.lower()
    if group in ('complaints', 'advice', 'timing'):
        w, g = want.lower(), got.lower()
        return any(x in g or fuzz.token_set_ratio(x, g) >= 70 for x in [w] + SYNONYMS.get(w, [])) or fuzz.token_set_ratio(w, g) >= 70
    if group in ('duration', 'follow_up'):
        return period(want) is not None and period(want) == period(got)
    if group == 'vitals':
        return re.sub(r'[^0-9./]', '', want) == re.sub(r'[^0-9./]', '', got)
    return compact(want) == compact(got)     # drug, dose


def expected_facts(sc):
    e, out = sc['expected'], []
    out += [('complaints', '', c) for c in e['chief_complaints']]
    out += [('vitals', k, v) for k, v in e['vitals'].items()]
    for rx in e['prescription']:
        out += [('drug', '', rx['drug']), ('dose', rx['drug'].lower(), rx['dose']),
                ('timing', rx['drug'].lower(), rx['timing']), ('duration', rx['drug'].lower(), rx['duration'])]
    out += [('advice', '', a) for a in e['advice']]
    out += [('follow_up', '', e['follow_up'])] if e['follow_up'] else []
    return out


def predicted_facts(rec):
    out = [('complaints', '', c) for c in rec.chief_complaints]
    out += [('vitals', k, v) for k, v in rec.vitals.model_dump().items() if v]
    for rx in rec.prescription:
        key = rx.drug.lower()
        out += [('drug', '', rx.drug)] + [(g, key, getattr(rx, f)) for g, f in (('dose', 'dose'), ('timing', 'timing'), ('duration', 'duration')) if getattr(rx, f)]
    out += [('advice', '', a) for a in rec.advice]
    out += [('follow_up', '', rec.follow_up)] if rec.follow_up else []
    return out


def match_facts(exp, pred):
    """Greedy one-to-one matching inside each group (and drug key). Returns matched expected, missed, extra."""
    pool, matched, missed = list(pred), [], []
    for g, k, v in exp:
        hit = next((p for p in pool if p[0] == g and p[1] == k and same(g, v, p[2])), None)
        (matched if hit else missed).append((g, k, v))
        if hit:
            pool.remove(hit)
    return matched, missed, pool


def hallucinations(rec):
    """Unverified items for facts a doctor could be harmed by: drug, dose, vitals, diagnosis, patient details."""
    bad = []
    for item in rec.inferred:
        path = item.split(' - ', 1)[-1].split(':')[0]
        if path.startswith(('vitals.', 'patient.')) or path == 'diagnosis' or path.endswith(('.drug', '.dose')):
            bad.append(item)
    return bad


def pct(n, d):
    return round(100 * n / d, 1) if d else None


def quantiles(xs):
    xs = sorted(xs)
    return {'p50': round(statistics.median(xs), 2), 'p95': round(xs[min(len(xs) - 1, int(0.95 * len(xs)))], 2), 'n': len(xs)} if xs else None


def speaker_accuracy(sc, utterances):
    """Share of reference turns whose best-matching predicted turn has the same role (only meaningful with diarization)."""
    if not any(u.speaker != 'unknown' for u in utterances):
        return None
    ok = 0
    for t in sc['turns']:
        best = max(utterances, key=lambda u: fuzz.partial_ratio(t['text'], u.text))
        ok += best.speaker == ('clinician' if t['speaker'] == 'clinician' else 'patient')
    return ok / len(sc['turns'])


def run_one(sc, mode, ab):
    timings, out = {}, {'id': sc['id']}
    transcript, utterances = '\n'.join(t['text'] for t in sc['turns']), []
    if mode == 'audio':
        wav = ROOT / 'eval' / 'audio' / f"{sc['id']}.wav"
        t0 = time.perf_counter()
        r = voice.transcribe(wav.read_bytes(), wav.name)
        timings['stt'] = time.perf_counter() - t0
        transcript, utterances = r['transcript'], r['utterances']
        out['transcript'] = transcript
        out['speaker_accuracy'] = speaker_accuracy(sc, utterances)
        if ab:
            drugs = [x['drug'] for x in sc['expected']['prescription']]
            saved = config.ENABLE_KEYTERMS
            out['keyterms_ab'] = {}
            for flag in (False, True):
                config.ENABLE_KEYTERMS = flag
                text = voice.transcribe(wav.read_bytes(), wav.name)['transcript'].lower()
                out['keyterms_ab']['with' if flag else 'without'] = [sum(d.lower() in text for d in drugs), len(drugs)]
            config.ENABLE_KEYTERMS = saved
    t0 = time.perf_counter()
    rec = llm.structure(transcript, utterances)
    timings['structure'] = time.perf_counter() - t0
    t0 = time.perf_counter()
    flags = {f.rule_id for f in redflags.check(rec)}
    timings['redflags'] = time.perf_counter() - t0
    matched, missed, extra = match_facts(expected_facts(sc), predicted_facts(rec))
    out.update(timings=timings, matched=matched, missed=missed, extra=extra, hallucinations=hallucinations(rec),
               flags_expected=sc['expected_red_flags'], flags_predicted=sorted(flags),
               extraction_failed=any(w.startswith('Automatic extraction failed') for w in rec.warnings), warnings=rec.warnings)
    return out


def summarize(results, scenarios):
    m = {}
    tp = ex = pr = 0
    per_group = {}
    for g in GROUPS:
        gt = sum(1 for r in results for f in r['matched'] if f[0] == g)
        ge = gt + sum(1 for r in results for f in r['missed'] if f[0] == g)
        gp = gt + sum(1 for r in results for f in r['extra'] if f[0] == g)
        p, rc = (gt / gp if gp else None), (gt / ge if ge else None)
        per_group[g] = {'precision': pct(gt, gp), 'recall': pct(gt, ge), 'expected': ge,
                        'f1': round(200 * p * rc / (p + rc), 1) if p and rc else (0.0 if ge else None)}
        tp, ex, pr = tp + gt, ex + ge, pr + gp
    m['overall_f1'] = round(200 * tp / (ex + pr), 1) if ex + pr else None   # micro F1 = 2TP / (expected + predicted)
    m['per_field'] = per_group
    m['drug_exact'], m['dose_exact'] = per_group['drug']['recall'], per_group['dose']['recall']
    m['hallucinations'] = sum(len(r['hallucinations']) for r in results)
    m['hallucination_items'] = [(r['id'], h) for r in results for h in r['hallucinations']]
    ftp = sum(len(set(r['flags_expected']) & set(r['flags_predicted'])) for r in results)
    fpred = sum(len(r['flags_predicted']) for r in results)
    fexp = sum(len(r['flags_expected']) for r in results)
    m['redflag_precision'], m['redflag_recall'] = pct(ftp, fpred), pct(ftp, fexp)
    sa = [r['speaker_accuracy'] for r in results if r.get('speaker_accuracy') is not None]
    m['speaker_accuracy'] = pct(sum(sa), len(sa)) if sa else None
    ab = [r['keyterms_ab'] for r in results if 'keyterms_ab' in r]
    m['keyterms_drug_names'] = {k: f"{sum(a[k][0] for a in ab)}/{sum(a[k][1] for a in ab)}" for k in ('without', 'with')} if ab else None
    m['extraction_failures'] = sum(r['extraction_failed'] for r in results)
    stages = {s for r in results for s in r['timings']}
    m['latency_s'] = {s: quantiles([r['timings'][s] for r in results if s in r['timings']]) for s in sorted(stages)}
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--mode', choices=['text', 'audio'], default='text')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--diarize', action='store_true')
    ap.add_argument('--keyterms', action='store_true')
    ap.add_argument('--keyterms-ab', action='store_true')
    ap.add_argument('--no-latest', action='store_true', help='write only eval/results/, leave eval/reports/latest.json alone')
    a = ap.parse_args()
    if not (a.all or a.only):
        ap.error('pass --all or --only IDS')
    config.MOCK_MODE = False
    config.ENABLE_DIARIZATION, config.ENABLE_KEYTERMS = a.diarize, a.keyterms
    scenarios = synthesize_audio.load()
    if a.only:
        scenarios = [s for s in scenarios if s['id'] in a.only.split(',')]
    if a.mode == 'audio':
        missing = [s['id'] for s in scenarios if not (ROOT / 'eval' / 'audio' / f"{s['id']}.wav").exists()]
        if missing:
            sys.exit(f'Missing audio for {missing}. Run eval/synthesize_audio.py --yes first.')
    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(lambda s: run_one(s, a.mode, a.keyterms_ab), scenarios))
    rep = {
        'run_id': report.run_id(), 'mode': a.mode, 'scenario_count': len(scenarios),
        'synthetic': 'All scenarios are synthetic scripts' + ('; audio is Bulbul speech, not real clinic audio.' if a.mode == 'audio' else '; no audio or STT in this run (text mode).'),
        'config': {'llm_model': config.LLM_MODEL, 'stt_model': config.STT_MODEL, 'stt_mode': config.STT_MODE, 'prompt_version': llm.PROMPT_VERSION,
                   'diarization': a.diarize, 'keyterms': a.keyterms},
        'metrics': summarize(results, scenarios),
        'scenarios': sorted(({'id': r['id'], 'missed': r['missed'], 'extra': r['extra'], 'hallucinations': r['hallucinations'],
                              'flags_expected': r['flags_expected'], 'flags_predicted': r['flags_predicted'],
                              'extraction_failed': r['extraction_failed'], 'issues': len(r['missed']) + len(r['extra'])} for r in results),
                            key=lambda s: -s['issues']),
    }
    failures = report.gate(rep, report.load_latest())
    rep['gate'] = {'passed': not failures, 'failures': failures}
    path = report.write(rep, latest=not a.no_latest)
    m = rep['metrics']
    print(f"run {rep['run_id']}  mode={a.mode}  scenarios={len(scenarios)}  -> {path.relative_to(ROOT)}")
    for k in ('overall_f1', 'drug_exact', 'dose_exact', 'redflag_precision', 'redflag_recall', 'hallucinations', 'speaker_accuracy', 'extraction_failures'):
        print(f'  {k:<22}{m[k]}')
    print('  per field F1:', {g: v['f1'] for g, v in m['per_field'].items()})
    print('  latency (s):', m['latency_s'])
    print('  worst scenarios:', [(s['id'], s['issues']) for s in rep['scenarios'][:5]])
    print('  gate:', 'PASSED' if not failures else 'FAILED: ' + '; '.join(failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
