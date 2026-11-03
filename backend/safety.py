"""Deterministic prescription safety checks (F24). Warnings for the clinician only: never edits the prescription,
never decided by an LLM. Rules are human-written in safety_rules.json."""
import json
from pathlib import Path

import config
import formulary
from schemas import ClinicalRecord, RedFlag

RULES_PATH = Path(__file__).resolve().parent / 'safety_rules.json'
UNREVIEWED = ' (rule not yet reviewed by a clinician)'


def load_rules(production=None):
    data = json.loads(RULES_PATH.read_text(encoding='utf-8'))
    production = config.PRODUCTION_MODE if production is None else production
    return [r for r in data['rules'] if r.get('reviewed_by') or not production]


def _key(name):
    return formulary.normalize(name or '').strip().lower()


def _warn(rule, matched, text):
    return RedFlag(rule_id=rule['id'], title=rule['title'] + ('' if rule.get('reviewed_by') else UNREVIEWED),
                   severity='warning', matched_inputs=matched, action_text=text)


def check(record: ClinicalRecord, production=None):
    rules = load_rules(production)
    drugs = [(rx.drug, _key(rx.drug)) for rx in record.prescription if rx.drug.strip()]
    out = []
    for rule in rules:
        t = rule['type']
        if t == 'duplicate_drug':
            seen = {}
            for raw, k in drugs:
                seen.setdefault(k, []).append(raw)
            for k, raws in seen.items():
                if len(raws) > 1:
                    out.append(_warn(rule, raws, f'{raws[0]} is listed {len(raws)} times. Check for a duplicate.'))
        elif t == 'same_class':
            members = {d.lower() for d in rule['drugs']}
            hit = sorted({raw for raw, k in drugs if k in members})
            if len({_key(h) for h in hit}) >= 2:
                out.append(_warn(rule, hit, f'Two {rule["class"]}s are prescribed: {" and ".join(hit)}. Confirm this is intended.'))
        elif t == 'allergy':
            allergies = {_key(a) for a in record.allergies if a.strip()}
            for raw, k in drugs:
                if k in allergies:
                    out.append(_warn(rule, [raw, f'allergy: {raw}'], f'{raw} matches a stated allergy. Do not prescribe without review.'))
    return out
