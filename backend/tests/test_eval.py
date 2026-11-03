import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'eval'))

import build_scenarios
import report
import run_eval
import synthesize_audio
from schemas import ClinicalRecord, Vitals, RxItem


def scenarios():
    return synthesize_audio.load(ROOT / 'eval' / 'scenarios.jsonl')


def test_scenario_file_is_complete_and_current():
    sc = scenarios()
    assert len(sc) >= 30 and len({s['id'] for s in sc}) == len(sc)
    assert {s['language'] for s in sc} == {'mr-IN', 'hi-IN', 'en-IN'}
    assert {'noisy', 'fast'} <= {t for s in sc for t in s['tags']}
    assert sum(bool(s['expected_red_flags']) for s in sc) >= 8
    rebuilt = [build_scenarios.build(*row[:1], *row[1:]) for row in build_scenarios.ROWS]
    assert rebuilt == sc, 'eval/scenarios.jsonl is stale: run python eval/build_scenarios.py'


def test_scenarios_never_reuse_the_prompt_few_shot_examples():
    import mock_data
    texts = ' '.join(t['text'] for s in scenarios() for t in s['turns'])
    for sid in ('S1', 'S2'):
        assert mock_data.SCENARIOS[sid]['transcript'] not in texts


def test_expected_values_are_stated_in_the_script():
    for s in scenarios():
        said = ' '.join(t['text'] for t in s['turns']).lower()
        for rx in s['expected']['prescription']:
            assert rx['drug'].lower() in said and rx['dose'].lower() in said
        for v in s['expected']['vitals'].values():
            assert v in said


def rec(**kw):
    return ClinicalRecord(**kw)


def test_scoring_matches_paraphrases_but_not_wrong_values():
    exp = [('advice', '', 'low salt'), ('vitals', 'bp', '150/95'), ('dose', 'metoprolol', '50mg'), ('follow_up', '', '1 week')]
    pred = [('advice', '', 'Eat less salt'), ('vitals', 'bp', '150 / 90'), ('dose', 'metoprolol', '50 mg'), ('follow_up', '', 'after 1 month')]
    matched, missed, extra = run_eval.match_facts(exp, pred)
    assert [f[0] for f in matched] == ['advice', 'dose'] and {f[0] for f in missed} == {'vitals', 'follow_up'}


def test_period_requires_the_same_number_and_unit():
    assert run_eval.period('for 2 weeks') == run_eval.period('two weeks') == ('2', 'week')
    assert not run_eval.same('duration', '30 days', '30 weeks') and run_eval.same('duration', '30 days', '30 days')


def test_hallucination_counts_only_unverified_critical_fields():
    r = rec(inferred=['Unverified, no matching quote - prescription.1.drug: Aspirin', 'Unverified, no matching quote - vitals.bp: 120/80',
                      'Unverified, no matching quote - prescription.0.frequency: once daily', 'Unverified, no matching quote - advice.0: x'])
    assert len(run_eval.hallucinations(r)) == 2


def report_with(**metrics):
    base = {'overall_f1': 95.0, 'drug_exact': 100.0, 'dose_exact': 100.0, 'redflag_precision': 100.0, 'redflag_recall': 100.0, 'hallucinations': 0}
    return {'mode': 'text', 'metrics': {**base, **metrics}}


def test_gate_fails_on_any_hallucination():
    assert report.gate(report_with(hallucinations=1), None)


def test_gate_fails_on_a_drop_over_two_points_only():
    prev = report_with()
    assert report.gate(report_with(overall_f1=92.9), prev)
    assert report.gate(report_with(overall_f1=93.0), prev) == []
    assert report.gate(report_with(redflag_recall=90.0), prev)


def test_gate_does_not_compare_different_modes():
    prev = {**report_with(), 'mode': 'audio'}
    assert report.gate(report_with(overall_f1=50.0), prev) == []


def test_noise_is_deterministic_and_changes_the_audio():
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b''.join(int(8000 * (1 if i % 40 < 20 else -1)).to_bytes(2, 'little', signed=True) for i in range(4000)))
    clean = buf.getvalue()
    assert synthesize_audio.add_noise(clean) == synthesize_audio.add_noise(clean) != clean


def test_estimate_counts_one_tts_call_per_turn():
    sc = scenarios()
    assert synthesize_audio.estimate(sc)['bulbul_tts_calls'] == sum(len(s['turns']) for s in sc)


def test_latest_report_is_a_real_committed_run():
    data = json.loads((ROOT / 'eval' / 'reports' / 'latest.json').read_text(encoding='utf-8'))
    assert data['scenario_count'] >= 30 and data['metrics']['hallucinations'] == 0
    # The gate result is recorded as it happened (the final audio run failed it on speech-model variation: see docs/EVAL.md).
    assert set(data['gate']) == {'passed', 'failures'} and (data['gate']['passed'] or data['gate']['failures'])


def test_devanagari_prompt_example_uses_no_eval_drug_or_complaint():
    import llm
    texts = ' '.join(t['text'] for s in scenarios() for t in s['turns'])
    out = llm.DEVANAGARI_EXAMPLE['output']
    assert out['prescription'][0]['drug'] not in texts and 'पाठदुखी' not in texts
