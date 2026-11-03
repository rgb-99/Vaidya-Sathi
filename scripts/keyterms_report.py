"""Drug-name accuracy on the demo clips with and without key terms (F19). Run from repo root:
python scripts/keyterms_report.py   (real API, REST path; reuses the metrics of compare_stt.py)
It prints the numbers only. An improvement is claimed in docs only if these numbers show one."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))

import compare_stt as m
import config
import formulary
import sarvam_client

config.MOCK_MODE = False
rows = []
for clip in sorted(p for p in (ROOT / 'demo' / 'audio').glob('S*.wav')):
    ref = (ROOT / 'demo' / 'transcripts' / f'{clip.stem}.txt').read_text(encoding='utf-8').strip()
    drugs = m.drug_names(ref)
    for label, terms in (('without', None), ('with', formulary.key_terms())):
        hyp = sarvam_client.stt(clip, keyterms=terms)['transcript']
        toks = m.normalize(hyp)
        rows.append((clip.stem, label, m.found(drugs, toks, ' '.join(toks)), len(drugs), m.wer(m.normalize(ref), toks)))

print(f"{'clip':<6}{'keyterms':<10}{'drugs':>7}{'WER':>7}   (mode={config.STT_MODE}, model={config.STT_MODEL})")
for clip, label, ok, n, w in rows:
    print(f"{clip:<6}{label:<10}{f'{ok}/{n}' if n else 'n/a':>7}{w:>7.2f}")
for label in ('without', 'with'):
    sel = [r for r in rows if r[1] == label]
    print(f"TOTAL {label:<8} drugs {sum(r[2] for r in sel)}/{sum(r[3] for r in sel)}   mean WER {sum(r[4] for r in sel) / len(sel):.2f}")
