# Railway Deployment — Worker

Step-by-step, mit genauen Klicks und copy-paste env-Werten.

## 1. Railway-Account + neues Projekt

1. Öffne <https://railway.app> → **Sign in with GitHub** (mit deinem `moritz@ecomtorials.de` GitHub-Account)
2. Wenn du noch kein Railway-Projekt hast: Railway fragt nach einer Billing-Methode — Kreditkarte hinzufügen (kostenlos bis $5/Monat, darüber Pay-as-you-go).
3. Auf der Railway-Startseite: **+ New Project** → **Deploy from GitHub repo**
4. Wenn GitHub-Zugriff noch nicht erlaubt: **Configure GitHub App** → wähle die `ecomtorials` Org → "Only select repositories" → wähle `ecomtorials-research-hub` → **Save**
5. Zurück zu Railway → suche nach `ecomtorials-research-hub` → **Deploy Now**

Railway erstellt automatisch einen Service — aber er wird fehlschlagen (weil er versucht, aus dem Repo-Root zu bauen, aber der Worker liegt in `apps/worker/`). Das fixen wir gleich.

## 2. Service-Settings korrigieren

1. Klick auf den Service (der gerade fehlschlägt)
2. Tab **Settings** links
3. Scroll zu **Source** Sektion:
   - **Root Directory:** `apps/worker`
   - **Watch Paths:** `apps/worker/**, packages/shared/**` (optional, verhindert unnötige Rebuilds bei reinen Frontend-Changes)
   - **Build Method:** Dockerfile (sollte automatisch erkannt werden, da `apps/worker/Dockerfile` existiert)

4. Scroll zu **Deploy** Sektion:
   - **Start Command:** (leer lassen — wird aus Dockerfile `CMD` genommen)
   - **Healthcheck Path:** `/healthz`
   - **Healthcheck Timeout:** `30`
   - **Restart Policy:** `ON_FAILURE`, Max Retries `3`

5. Scroll zu **Networking**:
   - **Generate Domain** klicken → notiere die URL, z.B. `ecomtorials-research-hub-production.up.railway.app`

## 3. Environment Variables

Tab **Variables** → **+ New Variable** → für jeden der folgenden Einträge:

**Copy-paste Template (Werte aus `railway-secrets.md` und `credentials`-Tabelle einsetzen):**

```
WORKER_SHARED_SECRET=<siehe Desktop/railway-secrets.md — identisch mit RESEARCH_WORKER_SECRET in Vercel>

SUPABASE_URL=https://zxpweqryywixicirxkwu.supabase.co

SUPABASE_SERVICE_ROLE_KEY=<aus credentials-Tabelle: service_name='supabase_knowledge_base'>

ANTHROPIC_API_KEY=<aus credentials-Tabelle: service_name='anthropic'>

PERPLEXITY_API_KEY=<aus credentials-Tabelle: service_name='perplexity'>

GEMINI_API_KEY=<aus credentials-Tabelle: service_name='gemini' — einen der 7 Keys wählen>

CROSSREF_EMAIL=research@ecomtorials.de

ARTIFACT_BUCKET=research-reports
```

**Die konkreten Werte liegen lokal in `C:\Users\PCUser\Desktop\railway-secrets.md`** (nicht im Git-Repo, weil GitHub-Secret-Scanning sonst den Push blockt). Diese Datei zum Copy-Paste nutzen, NICHT committen.

**Tipp:** Railway hat einen **Raw Editor** unter Variables — einmal klicken und alle Variablen auf einmal einfügen (1 Zeile pro Variable, leere Zeilen werden ignoriert).

### Google Service Account JSON

Extra Schritt wegen Länge. Füge eine neue Variable hinzu:
- **Name:** `GOOGLE_SERVICE_ACCOUNT_JSON`
- **Value:** Inhalt von `C:\Users\PCUser\Desktop\railway-gcp-sa-base64.txt` (Base64-String, ~3200 Zeichen, eine Zeile)

Der Worker-Code (`drive.py`) akzeptiert entweder Base64 oder rohen JSON — Base64 ist robuster weil Railway Multi-Line-Werte manchmal kaputt escape.

## 4. Redeploy

Variables-Änderungen triggern automatisch einen Redeploy. Falls nicht:
- Tab **Deployments** → **⋮** beim neuesten Deployment → **Redeploy**

Deploy-Logs beobachten (Tab **Deployments** → Klick auf den laufenden Deploy):
- Zeile `Running on http://0.0.0.0:8000` = Worker läuft
- Zeile `uvicorn running` = bereit für Requests

## 5. Healthcheck + Verbindung zu Vercel

Nach erfolgreichem Deploy:

```bash
curl https://<deine-railway-url>/healthz
```

Erwartete Antwort: `{"ok":true,"service":"research-worker"}`

Dann in **Vercel** die Worker-URL aktualisieren:
1. <https://vercel.com/ecomtorials-gmbhs-projects/ecomtorials-research-hub/settings/environment-variables>
2. `RESEARCH_WORKER_URL` bearbeiten → Wert: `https://<deine-railway-url>` (ohne trailing slash)
3. Save
4. **Deployments** Tab → neuesten Deploy → **⋮** → **Redeploy** (damit die neue URL übernommen wird)

## 6. E2E-Test

1. Öffne <https://ecomtorials-research-hub.vercel.app>
2. Login mit Google (@ecomtorials.de)
3. **+ Neue Research** → Kunde wählen → Mode **Custom** → nur `step0_scrape` und `assembly_export` ankreuzen (~$0.05 test-run)
4. Angle: "Testlauf Infrastruktur"
5. URL: die Default-Page-URL des Kunden
6. Submit → Job-Detail-Seite öffnet sich
7. Innerhalb 2-3 min sollte `step0_scrape` auf running und dann succeeded gehen
8. Bei `assembly_export` succeeded → Check: Drive-Ordner des Kunden sollte einen neuen Unterordner `Research YYYY-MM-DD - custom - <Brand>/` enthalten

Falls Fehler: **Logs** Tab im Railway-Service öffnen — dort siehst du Stack Traces vom Worker.

## Troubleshooting

**"Docker build failed: pipeline/mcp-server/requirements.txt not found":**
`Watch Paths` oder `Root Directory` falsch gesetzt. Muss `apps/worker` sein (ohne Trailing Slash).

**"invalid signature" (401) vom Worker:**
`WORKER_SHARED_SECRET` (Railway) ≠ `RESEARCH_WORKER_SECRET` (Vercel). Beide müssen identisch sein. Copy-paste geht leicht kaputt bei Whitespace — verifiziere mit `echo -n "$WORKER_SHARED_SECRET" | wc -c` = 64.

**Worker startet aber Jobs bleiben "queued":**
Vercel kann Worker-URL nicht erreichen. Check: `RESEARCH_WORKER_URL` in Vercel enthält `https://` und keinen Trailing-Slash.

**Drive-Upload scheitert "insufficient scopes":**
Service-Account braucht zusätzlich Drive-Share auf den Kunden-Ordner. In Drive: Kunden-Root-Ordner → Teilen → `ecomtorialsdashboardv3@ecomtorials-automation.iam.gserviceaccount.com` → Rolle **Inhalt-Manager**.

**Pipeline hängt bei R1a/R1b:**
Perplexity-Rate-Limit erreicht. Die Pipeline hat Retry+Backoff am Tool-Layer — warten. Sollte nach 30-60s weiterlaufen.
