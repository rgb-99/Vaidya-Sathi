# Sarvam AI — API Notes

> Summary of the Sarvam docs pages relevant to Vaidya Saathi.
> Update this file whenever a new endpoint or parameter is discovered.

---

## SDK Installation

```bash
pip install -U sarvamai
```

## Authentication

```python
from sarvamai import SarvamAI
client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
```

- Key goes in `.env` as `SARVAM_API_KEY=`.
- Never hardcode or print the key.

---

## Speech-to-Text (Saaras)

```python
r = client.speech_to_text.transcribe(
    file=open(path, "rb"),
    model="saaras:v4",
    mode="codemix",      # chosen in M1, see DECISIONS.md
)
transcript = r.transcript
```

- **Model:** `saaras:v4` (current). `saarika` is deprecated — do not use.
- **Accepted formats (REST and Batch):** MP3, WAV, AAC, AIFF, OGG/Opus, FLAC, MP4/M4A, AMR, WMA, WebM, PCM. Codec is auto-detected; PCM needs `input_audio_codec` and 16 kHz. WebSocket streaming accepts only WAV and raw PCM. Best accuracy: 16 kHz mono 16-bit WAV.
- **Max duration:** REST is **30 s per request**. Batch API: up to 2 h per file, 20 files per job. Our choice: chunk to <=28 s and call REST (cut at silences), reject over `MAX_AUDIO_SECONDS` (180). Batch is the path for longer audio and for diarization.
- **File size:** no limit stated on the pages read ("file too large" is listed as a cause of 422).
- **Language:** `language_code` takes BCP-47 codes (`hi-IN`, `mr-IN`, `en-IN`, 21 more) or `unknown` for auto-detect. We send `unknown`.
- **Response (`SpeechToTextResponse`):** `request_id`, `transcript`, `language_code` (null if none detected), `language_probability` (when auto-detecting), and `timestamps` only if `with_timestamps=True`: chunk-level (sentence/phrase) `words`, `start_time_seconds`, `end_time_seconds`, not word-level.
- **Modes:** `transcribe` (default), `translate`, `verbatim`, `translit`, `codemix`; the REST guide says they work with `saaras:v4`. (The API reference table says "applies only to saaras:v3"; the REST guide, the keyterms page and the live API accepted `mode` with v4. We use it with v4.)
- **Diarization:** not on the REST endpoint. Batch API only (`num_speakers`, up to 20). Read the how-to page before M8.
- **Key-term prompting:** parameter `keyterms` (list of strings, max 50, 64 chars each), `saaras:v4` only, REST needs `sarvamai>=0.1.33a1`. Biases, does not guarantee. Installed SDK 0.1.43 accepts it.
- **Real-time streaming:** separate WebSocket endpoint (`saaras:v3-realtime`) — read the streaming docs before implementing.

---

## Chat Completions (LLM)

```python
r = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ],
)
text = r.choices[0].message.content
```

- **Models:**
  - `sarvam-105b` — reasoning and structuring.
  - `sarvam-105b-conversations` — dialogue and spoken-style text.
  - `sarvam-m` is deprecated — do not use.
- **Note:** reasoning models may wrap JSON in code fences — always strip fences before parsing.

---

## Text-to-Speech (Bulbul)

```python
r = client.text_to_speech.convert(
    language_code="mr-IN",
    text="...",
    model="bulbul:v4-flash",
    speaker="meera",       # pick valid names from the Voices page
)
wav_bytes = base64.b64decode("".join(r.audios))
```

- **Model:** `bulbul:v4-flash` (current).
- **Speakers:** check the Voices page in the docs for valid speaker names per language.
- **Character limit:** REST 2,500 chars per request (HTTP streaming 3,500; WebSocket 2,500 per message). Split on sentence boundaries if needed.
- **Languages supported:** docs list 10 Indian languages plus English — verify the exact list.

---

## Document Intelligence (Vision)

Verified in M11 (SDK 0.1.43 introspection plus a live run on 2026-11-03; the docs overview names the operations but gives no signatures):

- Namespace `client.doc_ai`: `parse()`, `extract()`, `split()`, `classify()`, `get_status(job_id)`, `get_results(job_id)`, `get_download_url(job_id)`, `create_upload_url()`, `get_capabilities()`. Supersedes the older Document Digitization API.
- **Extract** (specific values): `client.doc_ai.extract(file=[(filename, bytes_or_file, mime)], schema=<JSON-schema string>, output_format='json')` returns `job_id`, `status='pending'`, `run_id`. Poll `get_status(job_id).status` (seen: `pending`, `completed`; failure state names are not documented, so `failed`, `error`, `cancelled` are treated as failures). Then `get_results(job_id)` returns `.result` (our schema, e.g. `{"medicines": [{drug, dose, frequency, duration}]}`) and `.annotations` (per field `confidence` 0 to 1 and the source region on the page) and `.usage` (page counts).
- **Parse** (whole page as text): `parse(file=[...], language=..., content_type='printed'|'handwritten'|'mixed')`, fetch with `get_download_url`; output HTML, Markdown or JSON. Not used by the app.
- Accepted types: PNG, JPG and PDF worked or are listed; no size or page limit was found on the pages read. The app enforces its own 10 MB limit.
- Live result: all three synthetic samples (printed text in a handwriting-style font) were read completely at confidence 1.0 in a few seconds. Real handwriting is untested.

---

## Error Handling

- Catch `ApiError` from `sarvamai.core.api_error`.
- Handle: 400 (bad request), 403 (bad key), 422 (invalid params), 429 (rate limit — retry once with backoff).

---

## Verified from docs.sarvam.ai (2026-11-03, M0)

- [x] Chat: `client.chat.completions(model=..., messages=[...])`, reply in `response.choices[0].message.content` (V1 API). Smoke test passed against `sarvam-105b-conversations`.
- [x] `sarvam-105b-conversations` exists only on V1 (`chat.completions`); `sarvam-105b` is on V1 and V2.
- [x] Chat extras: `temperature` (0-2), `max_tokens` (default 2048, reasoning tokens count), `reasoning_effort` (`low`/`medium`/`high`, `None` disables), `response_format` (`json_schema`/`json_object`/`text`). Useful for M2.
- [x] Errors: `ApiError` (from `sarvamai.core.api_error`) has `status_code` and `body`. 429 is `TooManyRequestsError`, 403 `ForbiddenError` (bad key). 402 (credits exhausted) has no dedicated class: check `status_code`. Client timeouts raise `httpx.TimeoutException`, not `ApiError`.

## TODO

- [x] Confirm accepted audio formats and max duration for STT. (M1: formats above; 30 s REST limit.)
- [x] Confirm TTS character limit per request. (2,500 on REST.)
- [x] List all valid speaker names per language. (Enough for the app: verified with the live API 2026-11-03: bn-IN `arnab_bn_conversation`, gu-IN `bhavik_gu_conversation`, kn-IN `chaitra_kn_conversation`, pa-IN `anand_pa_conversation`, ta-IN `gokul_ta_narration`, te-IN `kavitha_te_conversation`. No ml-IN or od-IN voice name was accepted, so those two languages are not offered. Earlier notes: the SDK type lists 200+ names; on 2026-11-03 these worked with `bulbul:v4-flash`: mr-IN `ishita_mr_conversational`, `nilesh_mr_conversation`; hi-IN `rahul_hi_conversational`, `amit_hi_conversational`, `kavya_hi_conversational`. Short names such as `ritu`, `shubh`, `rahul` were rejected with 400. en-IN still to test. Do not set `TTS_SPEAKER_*` until M3 listening tests.)
- [x] Confirm diarization parameter name. (Batch API only: `client.speech_to_text_job.create_job(model='saaras:v4', mode=..., language_code='unknown'|..., with_diarization=True, num_speakers=None|1..20, keyterms=[...])`, then `job.upload_files(file_paths=[...])`, `job.start()`, `job.wait_until_complete(timeout=...)`, `job.get_file_results()`, `job.download_outputs(output_dir=...)`. Output `0.json` has `transcript`, `language_code`, `diarized_transcript.entries[{speaker_id, transcript, start_time_seconds, end_time_seconds}]`; timestamps are chunk-level; speaker ids were `"1"`, `"2"`. Limits: 2 h per file, 20 files per job, 20 speakers. Live test: 3-turn, 2-voice, 15 s clip took 9 s and separated the speakers correctly.)
- [x] Confirm key-term prompting parameter name. (`keyterms`, v4 only.)
- [x] List all supported TTS languages. (SDK type for `bulbul:v4-flash` calls: bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, od-IN, pa-IN, ta-IN, te-IN. Verify against the docs Voices page before M8.)
- [x] Pick one verified speaker per language (mr-IN, hi-IN, en-IN) and put them in `.env`. (Set in `.env.example`: `ishita_mr_conversational`, `kavya_hi_conversational`, `ritu_en_medical`. API-verified, NOT yet listened to: run `python scripts/test_voice.py <lang> <speaker> "text"` and swap if they sound wrong.)
      Test each with `python scripts/test_voice.py mr-IN <speaker> "नमस्कार"`.


## Real-time streaming STT (verified in M12, 2026-11-03)

- SDK: `AsyncSarvamAI(...).speech_to_text_streaming.connect(model='saaras:v4', mode=..., language_code=..., sample_rate=16000, flush_signal=True, high_vad_sensitivity=True)` as an async context manager. Send with `await ws.transcribe(audio=<base64 WAV>, encoding='audio/wav', sample_rate=16000)`, ask for text now with `await ws.flush()`, read with `async for msg in ws` (`msg.type == 'data'` has `msg.data.transcript`; `'events'` carry VAD signals). Only WAV or raw PCM is accepted; the SDK helper sends WAV.
- Without flushing, the whole transcript came back only after the audio ended (20 s for a 19.5 s clip) because the service segments on pauses. Calling `flush()` every 2 chunks of 1 s gave a segment about every second.
- The docs pages did not document the raw frame format, chunk size or concurrency limits; the `data` key and `is_final` are not confirmed.
