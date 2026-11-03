"""Stream a recorded clip through /api/stream in 1 s chunks and compare the final record with the normal path.
Run from repo root with the backend up (ENABLE_STREAMING=true, MOCK_MODE=false):
  python scripts/stream_check.py clip_16k.wav [language [original.wav]]   (original.wav: also compare the final record with the batch path)"""
import asyncio
import io
import json
import sys
import time
import wave

import websockets


def chunks(path, seconds=1.0):
    """16 kHz mono WAV chunks of the clip (the format the relay expects)."""
    with wave.open(path) as r:
        assert (r.getframerate(), r.getnchannels(), r.getsampwidth()) == (16000, 1, 2), 'convert first: ffmpeg -i in -ar 16000 -ac 1 out.wav'
        n = int(16000 * seconds)
        while frames := r.readframes(n):
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(frames)
            yield buf.getvalue()


async def main(path, language):
    t0, first = time.time(), None
    async with websockets.connect(f'ws://localhost:8000/api/stream?language={language}', max_size=None) as ws:
        async def send():
            for c in chunks(path):
                await ws.send(c)
                await asyncio.sleep(1.0)   # real-time pace
            await ws.send('end')
        sender = asyncio.create_task(send())
        async for raw in ws:
            msg = json.loads(raw)
            if msg['type'] == 'partial':
                first = first or time.time() - t0
                print(f'[{time.time() - t0:4.1f}s] {msg["text"]}')
            elif msg['type'] == 'done':
                print(f'first words after {first:.1f}s; final transcript:\n{msg["transcript"]}')
                break
            else:
                print(msg)
                break
        await sender
        return msg.get('transcript', '')

def compare(clip_16k, original, language, streamed):
    """Final record from the streamed transcript vs the record from the normal (batch) path on the same clip."""
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
    import config, llm, voice
    config.MOCK_MODE = False
    batch_text = voice.transcribe(Path(original).read_bytes(), Path(original).name)['transcript']
    def facts(rec):
        out = {f'vitals.{k}': v for k, v in rec.vitals.model_dump().items() if v}
        for rx in rec.prescription:
            out[f'rx.{rx.drug.lower()}'] = rx.dose.replace(' ', '').lower().replace('milligram', 'mg')
        out['complaints'] = ', '.join(sorted(rec.chief_complaints))
        return out
    a, b = facts(llm.structure(batch_text)), facts(llm.structure(streamed))
    same = {k for k in a if k in b and (a[k] == b[k] or k == 'complaints')}
    print(f'compare: {len(same)}/{len(a)} batch facts reproduced by streaming (complaints are compared by presence only)')
    for k in sorted(set(a) | set(b)):
        if k not in same:
            print(f'   differs {k}: batch={a.get(k)!r} stream={b.get(k)!r}')


if __name__ == '__main__':
    clip, lang = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'unknown'
    transcript = asyncio.run(main(clip, lang))
    if len(sys.argv) > 3:   # python scripts/stream_check.py clip_16k.wav mr-IN original.wav
        compare(clip, sys.argv[3], lang, transcript)
