# Deploying

The frontend is a static Vite build on **Vercel**. The backend runs on **Render** as a Docker container (`Dockerfile`, `render.yaml`), because it needs things Vercel functions do not have: ffmpeg for every transcription, a disk for SQLite (sign-offs, share links, history, analytics, the sign-off key), WebSockets for live mode, and background threads for prescription photos. The browser calls the backend directly (`VITE_API_BASE`): Vercel's proxy has a 30 s limit on proxied requests, which a slow extraction with a retry can exceed.

The app has no login. Anyone with the URL can use it, and in real mode every use spends Sarvam credits on your key. Share the URL only with people you trust, and use fake patients only.

## 1. Backend on Render

1. Push the repo to GitHub.
2. Render dashboard: **New → Blueprint**, pick the repo. It reads `render.yaml` and creates `vaidya-saathi-api` (Docker, Starter plan, 1 GB disk at `/app/data`). The disk needs a paid instance; on the free plan records vanish on every deploy.
3. Fill the variables marked `sync: false`:
   - `SARVAM_API_KEY`: your key (never commit it).
   - `TTS_SPEAKER_MR`, `TTS_SPEAKER_HI`, `TTS_SPEAKER_EN`: the voice names from your local `.env`. Any other variables you changed locally (for example `ENABLE_STREAMING`) can be added the same way.
   - `CORS_ORIGIN` and `PUBLIC_BASE_URL`: put a placeholder for now, set them in step 3.
4. When it is live, check `https://<backend>.onrender.com/api/health` returns `{"status":"ok","mock":false}`.

## 2. Frontend on Vercel

1. Vercel dashboard: **Add New → Project**, import the repo, set **Root Directory** to `frontend` (it reads `frontend/vercel.json`).
2. Environment variable: `VITE_API_BASE` = `https://<backend>.onrender.com` (no trailing slash needed). It is baked in at build time, so redeploy after changing it.
3. Deploy and note the URL, e.g. `https://vaidya-saathi.vercel.app`.

## 3. Connect them

On Render set `CORS_ORIGIN` and `PUBLIC_BASE_URL` to the exact Vercel URL (no trailing slash) and redeploy. `CORS_ORIGIN` allows one origin, so Vercel preview URLs are blocked; use the production URL.

## Check

Open the Vercel URL, tap **S2** under "Try a demo", **Extract details**, see both red flags, sign, **Make summary**, play it, then **Phone link (QR)** and open the link.
