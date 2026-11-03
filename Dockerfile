# Backend image (FastAPI + ffmpeg). The frontend is hosted separately (see docs/DEPLOY.md).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# The backend reads demo clips and transcripts, the committed eval report and safety rules from the repo.
COPY backend backend
COPY demo demo
COPY eval/reports eval/reports

# SQLite and the sign-off key live in /app/data: mount a persistent disk there.
RUN mkdir -p data
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
