# ecomtorials Research Hub

Web-App für ecomtorials-Mitarbeiter, um Full-, Angle-, UMP/UMS- und Custom-Research-Reports über die bestehende `ecomtorials-research-pipeline` zu generieren.

## Architektur

```
┌─────────────────────────┐      ┌──────────────────────────┐
│ apps/web (Next.js 15)   │──────│  Supabase Knowledge Base │
│  Vercel                 │      │  (zxpweqryywixicirxkwu)  │
│  research.ecomtorials.de│      │  - Auth (Google SSO)     │
└──────────┬──────────────┘      │  - research.jobs         │
           │  HMAC POST           │  - research.job_steps    │
           ▼                      │  - research.job_artifacts│
┌─────────────────────────┐      │  - Storage (MD/DOCX)     │
│ apps/worker (FastAPI)   │──────│  - Realtime (jobs/steps) │
│  Railway                │      └──────────────────────────┘
│  + vendored pipeline    │              │
└──────────┬──────────────┘              │
           │                              │
           ▼                              ▼
   Perplexity / CrossRef / PubMed   Google Drive
   (via MCP server)                 (Service Account)
```

## Packages

| Path | Beschreibung |
|---|---|
| `apps/web` | Next.js + React 19 + Tailwind v4. Login, Dashboard, New-Job-Form, Live-Progress, Result-Viewer, MD/DOCX-Download |
| `apps/worker` | Python 3.11 + FastAPI. Signiertes `/jobs`-Endpoint, Dispatch auf 4 Modi, Progress-Push, Storage- und Drive-Upload |
| `apps/worker/pipeline` | Vendored `ecomtorials-research-pipeline` (unangetastet) |
| `packages/shared` | `JobPayload`, `PipelineStep`, `JobStatus`, HMAC-Signing-Helpers (TypeScript) |
| `supabase/migrations` | SQL für `research.*` Schema + Storage-Bucket |

## Modi

| Mode | Steps | Runtime | Kosten | Use-Case |
|---|---|---|---|---|
| **Full** | Step 0 → R1a + R1b + R2-VoC + R3-Prefetch (parallel) → R2-Synth + R3-Scientist → QR → Repair → Export | ~27 min | ~$2.77 | Kunden-Onboarding |
| **Angle** | Step 0 → R1a (angle-fokussiert) + R2-VoC (parallel) → R2-Synth → Export | ~12-15 min | ~$1.20 | Kampagnen-Angle-Research |
| **UMP-Only** | R3-Prefetch → R3-Scientist (auf Basis einer vorherigen Full-Research) → Export | ~6-8 min | ~$3.50 | Separate UMP/UMS-Konstruktion |
| **Custom** | Freie Step-Auswahl mit Dependency-Validator | variabel | variabel | Power-User |

## Setup (Lokal)

### Voraussetzungen
- Node.js 20+, pnpm 9+
- Python 3.11+
- Supabase-Projekt (bereits: `zxpweqryywixicirxkwu`)
- Anthropic / Perplexity / Gemini API-Keys
- Google Service-Account mit Drive-Zugriff

### Web-App
```bash
pnpm install
# .env.local ist bereits mit Supabase-Keys befüllt (via MCP aus credentials-Tabelle)
# GOOGLE_SERVICE_ACCOUNT_JSON muss noch gesetzt werden (aus Google Cloud Console)
pnpm dev:web   # http://localhost:3000
```

### Worker
```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r pipeline/mcp-server/requirements.txt
cd pipeline && npm install && cd ..
cp .env.example .env        # Keys eintragen
uvicorn main:app --reload --port 8000
```

## Manuelle Schritte vor Go-Live

1. **Supabase Auth: Google Provider aktivieren**
   - Dashboard → Authentication → Providers → Google
   - Client-ID/Secret aus Google Cloud Console (OAuth 2.0 Credentials)
   - In der Google-Config den "hd"-Parameter auf `ecomtorials.de` setzen (Domain-Restriction)

2. **Google Service-Account für Drive**
   - GCP Console → IAM & Admin → Service Accounts → Create
   - Rolle: Drive File Access
   - Key → JSON runterladen → als `GOOGLE_SERVICE_ACCOUNT_JSON` env setzen (raw JSON oder base64)
   - Service-Account-E-Mail zu jedem Kunden-Drive-Ordner (oder Root-Ordner) adden

3. **Perplexity API-Key** — muss ergänzt werden (nicht in `credentials`-Tabelle vorhanden), Keys bei [perplexity.ai/settings/api](https://perplexity.ai/settings/api)

4. **Railway deployment**
   - Neues Railway-Projekt → Deploy from GitHub (pointing at `apps/worker/`)
   - Alle env-Vars setzen (siehe `apps/worker/.env.example`)
   - `WORKER_SHARED_SECRET` muss mit `RESEARCH_WORKER_SECRET` im Vercel-Projekt matchen

5. **Vercel deployment**
   - Neues Vercel-Projekt → Root: `apps/web/`, Build: `pnpm build`, Install: `pnpm install`
   - Env-Vars aus `.env.local` (plus `RESEARCH_WORKER_URL` auf die Railway-URL)
   - Custom Domain: `research.ecomtorials.de` → CNAME auf Vercel

## Supabase Schema

Applied migrations (alle live in `zxpweqryywixicirxkwu`):
- `001_research_schema` — Tables, Enums, Triggers, RLS, Realtime
- `002_lock_function_search_path` — Security-Hardening
- `003_expose_schema_to_postgrest` — PostgREST `db_schemas` config
- `004_grant_anon_schema_usage` — Anon-Grant mit RLS-Denial
- `005_storage_bucket` — Private Storage-Bucket `research-reports`

## Status

Phase 1 — Foundation abgeschlossen (2026-04-20):
- [x] Monorepo scaffold
- [x] Supabase schema + RLS + Storage
- [x] Web-App (Login, Dashboard, New-Job, Job-Detail, Result, API-Route)
- [x] Python-Worker (4 Modi, HMAC-Verify, Progress-Push, Drive-Upload)
- [x] Dockerfile + Railway-Config

Nächste Phase: E2E-Test mit echtem Kunden, Google-SSO-Config, Railway-Deployment.
