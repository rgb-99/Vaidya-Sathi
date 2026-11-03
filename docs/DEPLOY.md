# Deploying

Live: **https://vaidya-saathi.vercel.app** (Vercel project `vaidya-saathi`, Hobby plan).

One Vercel project runs two services (`vercel.json`): `frontend` (the Vite build, with an SPA fallback so `/share/<token>` works) and `backend` (the FastAPI app as a container built from `Dockerfile`, which adds ffmpeg). Top-level rewrites send `/api/*` and `/demo/*` to the backend and everything else to the frontend, so both share one origin and `VITE_API_BASE` stays empty. `.vercelignore` keeps `.env`, `data/`, virtualenvs and `node_modules` out of the upload.

The app has no login. Anyone with the URL can use it, and every use spends Sarvam credits on your key. Share it only with people you trust, and use fake patients only.

## Limits of this setup (chosen to stay on Vercel's free plan)

- **Nothing is kept for long.** Vercel containers are stateless and stop after about 5 minutes without traffic. SQLite (`/app/data`) lives inside one instance, so signed records, share links, history, analytics and referral tickets disappear when it stops, and a request that lands on another instance does not see them. A QR share link works while the instance is warm, not days later. A host with a persistent disk (the `Dockerfile` runs anywhere, e.g. Railway with a volume at `/app/data`) fixes this.
- **Sign-off works across instances** because `SIGNING_KEY` is set as a Vercel secret (every instance verifies with the same key).
- **Uploads are capped at 4.5 MB** per request (Vercel). A 3-minute browser recording is well under that; a long uncompressed WAV upload is not.
- **5 minutes per request** (Hobby maximum).

## Environment variables (Production)

`SARVAM_API_KEY` and `SIGNING_KEY` (secrets), `TTS_SPEAKER_MR`, `TTS_SPEAKER_HI`, `TTS_SPEAKER_EN`, `MOCK_MODE=false`, `STT_MODE=codemix`, `PUBLIC_BASE_URL` and `CORS_ORIGIN` = `https://vaidya-saathi.vercel.app`. Model names use the defaults in `backend/config.py`. Add one with:

```bash
npx vercel env add NAME production
```

## Redeploy

```bash
npx vercel login                                  # once
npx vercel link --yes --project vaidya-saathi     # once, from the repo root
npx vercel deploy --prod
```

## Check

`https://vaidya-saathi.vercel.app/api/health` returns `{"status":"ok","mock":false}`. Then open the site, tap **S2** under "Try a demo", **Extract details**, see both red flags, sign, **Make summary**, play it, and open **Phone link (QR)**.
