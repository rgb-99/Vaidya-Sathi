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
    mode="transcribe",   # also try "codemix"
)
transcript = r.transcript
```

- **Model:** `saaras:v4` (current). `saarika` is deprecated — do not use.
- **Modes:** `transcribe`, `codemix` — test both on demo audio and keep whichever extracts better.
- **Accepted formats:** check docs for WAV/WebM support and max duration.
- **Diarization:** check the how-to page for the exact parameter and limits.
- **Key-term prompting:** check the how-to page for the parameter name.
- **Real-time streaming:** separate endpoint — read the streaming docs before implementing.

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
- **Character limit:** check docs for per-request limit; split on sentence boundaries if needed.
- **Languages supported:** docs list 10 Indian languages plus English — verify the exact list.

---

## Document Intelligence (Vision)

- Asynchronous job flow — read the Document Intelligence docs for `parse` or `extract`.
- Used for prescription photo reading (F15).
- Use fake prescriptions only.

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

- [ ] Confirm accepted audio formats and max duration for STT.
- [ ] Confirm TTS character limit per request.
- [ ] List all valid speaker names per language.
- [ ] Confirm diarization parameter name.
- [ ] Confirm key-term prompting parameter name.
- [ ] List all supported TTS languages.
- [ ] Pick one verified speaker per language (mr-IN, hi-IN, en-IN) and put them in `.env`.
      Test each with `python scripts/test_voice.py mr-IN <speaker> "नमस्कार"`.

