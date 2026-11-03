# Deploying

The frontend is a static Vite build on **Vercel** (project `vaidya-saathi`, https://vaidya-saathi.vercel.app). The backend runs on **Railway** as a Docker container (`Dockerfile`, `railway.json`) with a volume at `/app/data`.

Why not the backend on Vercel too: Vercel containers can run ffmpeg and WebSockets, but they are stateless and scale to zero after 5 minutes, so the SQLite file (sign-offs, share links, history, analytics, the sign-off key) would be lost, and the spec allows no database other than SQLite. The browser calls the backend directly (`VITE_API_BASE`) rather than through a Vercel rewrite, because Vercel lists a 30 s limit on proxied requests and an extraction with a retry can take longer.

The app has no login. Anyone with the URL can use it, and in real mode every use spends Sarvam credits on your key. Share the URL only with people you trust, and use fake patients only.

## Backend (Railway)

```bash
npx @railway/cli login
npx @railway/cli init --name vaidya-saathi-api        # once
npx @railway/cli up --detach                          # uploads the repo (minus .dockerignore) and builds the Dockerfile
npx @railway/cli volume add --mount-path /app/data    # once
npx @railway/cli domain                               # once: prints https://<name>.up.railway.app
```

Variables (`npx @railway/cli variables --set KEY=value`): `SARVAM_API_KEY`, `TTS_SPEAKER_MR`, `TTS_SPEAKER_HI`, `TTS_SPEAKER_EN` (from your local `.env`), `MOCK_MODE=false`, `STT_MODE=codemix`, and `CORS_ORIGIN` and `PUBLIC_BASE_URL` both set to the Vercel URL (no trailing slash; one origin only, so Vercel preview URLs are blocked). Model names default to the values in `.env.example`.

Check: `https://<backend>/api/health` returns `{"status":"ok","mock":false}`.

## Frontend (Vercel)

```bash
cd frontend
npx vercel login
npx vercel link --yes --project vaidya-saathi                  # once
npx vercel env add VITE_API_BASE production                     # the Railway URL; baked in at build time
npx vercel deploy --prod
```

## Check

Open the Vercel URL, tap **S2** under "Try a demo", **Extract details**, see both red flags, sign, **Make summary**, play it, then **Phone link (QR)** and open the link.
