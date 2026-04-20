# research-worker

FastAPI service that wraps the vendored `ecomtorials-research-pipeline` and executes jobs triggered by the Next.js frontend.

## Endpoints

- `GET  /healthz` — health check
- `POST /jobs` — signed job trigger. Headers: `x-research-hub-signature`, `x-research-hub-timestamp`. Body is a JSON `JobPayload`. Returns 202 immediately, then runs in background.

## Dispatch

```
full     → modes.run_full       (complete pipeline, ~27 min)
angle    → modes.run_angle      (R1a angle-focused + R2-VoC, ~12 min)
ump_only → modes.run_ump_only   (R3 on top of a prior Full job's artifacts, ~7 min)
custom   → modes.run_custom     (user-selected step list)
```

Progress is pushed to Supabase (`research.job_steps`, `research.jobs`). Artifacts are uploaded to Supabase Storage + Google Drive.

## Local dev

```bash
cd apps/worker
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r pipeline/mcp-server/requirements.txt
cd pipeline && npm install && cd ..
cp .env.example .env        # fill in keys
uvicorn main:app --reload --port 8000
```

Must match `RESEARCH_WORKER_SECRET` in the web app's `.env.local` for `WORKER_SHARED_SECRET`.

## Deployment (Railway)

- Dockerfile-based build, `railway.json` configures healthcheck + restart policy.
- Required env vars:
  - `WORKER_SHARED_SECRET`
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
  - `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`
  - `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON or base64)
  - `ARTIFACT_BUCKET` (default `research-reports`)
