"""Compare STT modes on every clip in demo/audio against demo/transcripts/<clip>.txt.
Run from repo root: python scripts/compare_stt.py [mode ...]   (default: transcribe codemix)
Uses the real API (MOCK_MODE is ignored) and the real backend pipeline (voice.transcribe).

Metrics
  WER      word error rate after normalising case, punctuation and Devanagari digits (lower is better)
  drugs    reference drug names found verbatim, case-insensitive. A drug name is any Latin-script word of 4+
           letters in the reference transcript (fake-patient demo texts only use drug names in Latin script).
  numbers  reference numbers (e.g. 150/95, 102) found verbatim in the hypothesis
Note: `transcribe` writes Indic words in native script and `codemix` keeps English words in Latin script, so
drug matches and WER can differ for that reason alone. The script prints numbers; it does not pick a winner.
"""
import re
import statistics
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import config
import sarvam_client
import voice

DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')


def normalize(text):
    text = unicodedata.normalize('NFC', text).translate(DEVANAGARI_DIGITS).lower()
    text = re.sub(r'(?<=\d)\s*/\s*(?=\d)', '/', text)         # '150 / 95' -> '150/95'
    text = re.sub(r'[^\w/]+', ' ', text)                      # drop punctuation (danda included)
    return text.split()


def wer(ref, hyp):
    """Word-level Levenshtein distance divided by reference length."""
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref) if ref else 0.0


def drug_names(ref_text):
    return sorted({w.lower() for w in re.findall(r'[A-Za-z]{4,}', ref_text) if w.lower() != 'mg'})


def numbers(ref_text):
    return re.findall(r'\d+(?:/\d+)?', ref_text)


def found(items, hyp_tokens, hyp_text):
    return sum(1 for x in items if x in hyp_tokens or x in hyp_text)


def main():
    modes = sys.argv[1:] or ['transcribe', 'codemix']
    config.MOCK_MODE = False
    if not config.SARVAM_API_KEY:
        sys.exit('SARVAM_API_KEY is empty. Paste your key into .env and run again.')

    clips = sorted(p for p in (ROOT / 'demo' / 'audio').glob('*.wav') if p.stem != 'mock')
    if not clips:
        sys.exit('No clips in demo/audio. Run scripts/synthesize_demo_clips.py or add recordings.')

    rows, hyps = [], []
    for mode in modes:
        config.STT_MODE = mode
        for clip in clips:
            ref_file = ROOT / 'demo' / 'transcripts' / f'{clip.stem}.txt'
            if not ref_file.exists():
                print(f'skip {clip.name}: no {ref_file.relative_to(ROOT)}')
                continue
            ref_text = ref_file.read_text(encoding='utf-8').strip()
            t0 = time.perf_counter()
            try:
                out = voice.transcribe(clip.read_bytes(), clip.name)
            except (voice.AudioError, sarvam_client.SarvamError) as e:
                print(f'{mode} {clip.name}: FAILED {e}')
                continue
            secs = time.perf_counter() - t0
            hyp_tokens = normalize(out['transcript'])
            hyp_text = ' '.join(hyp_tokens)
            drugs, nums = drug_names(ref_text), numbers(ref_text)
            rows.append({
                'mode': mode, 'clip': clip.stem, 'wer': wer(normalize(ref_text), hyp_tokens),
                'drugs': (found(drugs, hyp_tokens, hyp_text), len(drugs)),
                'nums': (found(nums, hyp_tokens, hyp_text), len(nums)),
                'lang': out['language'] or '-', 'secs': secs,
            })
            hyps.append((mode, clip.stem, out['transcript']))

    print(f"\n{'mode':<11}{'clip':<6}{'WER':>7}{'drugs':>8}{'numbers':>9}{'lang':>8}{'secs':>7}")
    for r in rows:
        d = f"{r['drugs'][0]}/{r['drugs'][1]}" if r['drugs'][1] else 'n/a'
        n = f"{r['nums'][0]}/{r['nums'][1]}" if r['nums'][1] else 'n/a'
        print(f"{r['mode']:<11}{r['clip']:<6}{r['wer']:>7.2f}{d:>8}{n:>9}{r['lang']:>8}{r['secs']:>7.1f}")

    print(f"\n{'mode':<11}{'mean WER':>9}{'drugs':>8}{'numbers':>9}{'mean secs':>10}")
    for mode in modes:
        rs = [r for r in rows if r['mode'] == mode]
        if not rs:
            continue
        dn, dt = sum(r['drugs'][0] for r in rs), sum(r['drugs'][1] for r in rs)
        nn, nt = sum(r['nums'][0] for r in rs), sum(r['nums'][1] for r in rs)
        print(f"{mode:<11}{statistics.mean(r['wer'] for r in rs):>9.2f}{f'{dn}/{dt}':>8}{f'{nn}/{nt}':>9}"
              f"{statistics.mean(r['secs'] for r in rs):>10.1f}")

    print('\nHypotheses')
    for mode, clip, text in hyps:
        print(f'[{mode} {clip}] {text}')


if __name__ == '__main__':
    main()
