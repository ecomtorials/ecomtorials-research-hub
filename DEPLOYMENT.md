# Deployment Guide

Step-by-step, exakt. Wenn du hier eine Stelle findest wo "ist ja klar" steht — sag Bescheid, ich mach es konkreter.

## Übersicht der manuellen Schritte

1. [Google Cloud: Service Account für Drive anlegen](#1-google-cloud-service-account-für-drive)
2. [Google Cloud: OAuth 2.0 Client für Supabase Auth](#2-google-cloud-oauth-20-client)
3. [Supabase Dashboard: Google-Provider aktivieren](#3-supabase-google-provider-aktivieren)
4. [Perplexity API-Key besorgen + in Supabase credentials speichern](#4-perplexity-api-key)
5. [Railway: Worker deployen](#5-railway-worker-deployment)
6. [Vercel: Web-App deployen](#6-vercel-web-app-deployment)
7. [DNS: research.ecomtorials.de](#7-dns-research-subdomain)
8. [E2E-Test mit echtem Kunden](#8-e2e-test)

---

## 1. Google Cloud: Service Account für Drive

**Ziel:** Ein technischer Account, der Dateien in die Kunden-Drive-Ordner hochladen darf.

1. Öffne <https://console.cloud.google.com/>
2. Projekt wählen (oder neu anlegen, z.B. `ecomtorials-automations`)
3. Sidebar → "APIs & Services" → "Library" → suche nach "Google Drive API" → **Enable**
4. Sidebar → "IAM & Admin" → "Service Accounts" → **+ Create Service Account**
   - Name: `research-hub-drive`
   - Description: `Drive uploads for Research Hub`
   - Klick **Create and Continue**
   - Rolle vergeben: keine auf Projektebene nötig (Zugriff läuft per Drive-Share)
   - Klick **Done**
5. Den neuen Service Account in der Liste anklicken → Tab **Keys** → **Add Key** → **Create new key** → JSON → **Create**. Die JSON-Datei wird automatisch heruntergeladen.
6. **Drive-Zugriff geben:** Öffne im Browser deinen obersten ecomtorials-Kunden-Ordner in Drive. Klick **Teilen** → E-Mail-Adresse des Service Accounts einfügen (steht in der JSON-Datei als `client_email`, Format: `research-hub-drive@xxx.iam.gserviceaccount.com`) → Rolle **Inhalt-Manager** → **Senden**.
   - Wenn alle Kunden-Ordner unter einem Root-Ordner liegen, reicht Share auf den Root — die Vererbung deckt alles ab.
   - Wenn jeder Kunden-Ordner separat liegt: für jeden den Share-Schritt wiederholen.

**Ergebnis:** Du hast eine JSON-Datei mit Private Key. Kopiere den kompletten Inhalt (einzeiliger String, inkl. `\n` in `private_key`) — den brauchen wir später als `GOOGLE_SERVICE_ACCOUNT_JSON`.

---

## 2. Google Cloud: OAuth 2.0 Client

**Ziel:** Damit sich Mitarbeiter mit ihrem `@ecomtorials.de` Google-Account einloggen können.

1. Gleiche GCP-Console, gleiches Projekt.
2. Sidebar → "APIs & Services" → "OAuth consent screen"
   - User Type: **Internal** (weil Google Workspace — dann sehen nur `@ecomtorials.de` User das überhaupt)
   - App name: `ecomtorials Research Hub`
   - User support email: `moritz@ecomtorials.de`
   - Developer contact: `moritz@ecomtorials.de`
   - Scopes: `userinfo.email`, `userinfo.profile`, `openid` (die drei Default-Scopes von Supabase Auth reichen)
   - Save
3. Sidebar → "APIs & Services" → "Credentials" → **+ Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Name: `Supabase Auth — Research Hub`
   - **Authorized redirect URIs** (beide hinzufügen):
     - `https://zxpweqryywixicirxkwu.supabase.co/auth/v1/callback`
     - `http://localhost:3000/auth/callback` (für lokale Dev)
   - Klick **Create**
4. Notiere dir: **Client ID** und **Client Secret** (Dialog schließen nicht vorher!)

---

## 3. Supabase Google-Provider aktivieren

1. Öffne <https://supabase.com/dashboard/project/zxpweqryywixicirxkwu/auth/providers>
2. Klappe **Google** auf
3. Toggle **Enable Sign in with Google** auf ON
4. Client ID + Client Secret aus Schritt 2 einfügen
5. **Authorized Client IDs:** hier nichts zusätzlich eintragen (leer lassen)
6. **Skip nonce checks:** aus (Default)
7. Save
8. Direkt darunter: Tab **URL Configuration** prüfen
   - **Site URL:** `https://research.ecomtorials.de` (setzen sobald DNS live, bis dahin `http://localhost:3000`)
   - **Redirect URLs** (eine pro Zeile, alle hinzufügen):
     - `https://research.ecomtorials.de/auth/callback`
     - `http://localhost:3000/auth/callback`

---

## 4. Perplexity API-Key

1. <https://www.perplexity.ai/settings/api> → Sign in → **+ Generate**
2. Kopiere den Key (`pplx-...`)
3. Key in Supabase credentials-Tabelle speichern (damit andere Tools auch drauf zugreifen):

```sql
INSERT INTO credentials (service_name, credential_type, credential_value, is_active)
VALUES ('perplexity', 'api_key', 'pplx-...', true);
```

Ausführen via Supabase SQL Editor oder Claude Code MCP.

---

## 5. Railway: Worker Deployment

1. <https://railway.app/> → **New Project** → **Deploy from GitHub repo**
2. Repo: `ecomtorials/ecomtorials-research-hub`
3. Railway fragt nach einem Service — wähle **Add a service** → **GitHub Repo**
4. **Settings** des Services:
   - **Root Directory:** `apps/worker`
   - **Builder:** Dockerfile (automatisch erkannt durch `apps/worker/Dockerfile`)
   - **Watch Paths:** `/apps/worker/**` (damit nur Worker-Änderungen rebuilden)
5. **Variables** Tab — alle setzen:

```
WORKER_SHARED_SECRET=<random 64-char hex — generiere mit: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))">
SUPABASE_URL=https://zxpweqryywixicirxkwu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<aus credentials-Tabelle "supabase_knowledge_base">
ANTHROPIC_API_KEY=<aus credentials "anthropic">
PERPLEXITY_API_KEY=<aus Schritt 4>
GEMINI_API_KEY=<aus credentials "gemini", einer der 7 Keys>
CROSSREF_EMAIL=research@ecomtorials.de
GOOGLE_SERVICE_ACCOUNT_JSON=<kompletter JSON-String aus Schritt 1, einzeilig>
ARTIFACT_BUCKET=research-reports
```

6. **Deploy**. Railway baut den Docker-Image (~5-7 min beim ersten Mal) und deployed.
7. **Domain** Tab → **Generate Domain** → notiere die URL (z.B. `ecomtorials-research-hub-production.up.railway.app`)
8. Test: `curl https://<railway-url>/healthz` → sollte `{"ok":true,"service":"research-worker"}` liefern.

---

## 6. Vercel: Web-App Deployment

1. <https://vercel.com/> → **Add New…** → **Project** → Import Git Repository → `ecomtorials/ecomtorials-research-hub`
2. Configure Project:
   - **Framework Preset:** Next.js (sollte automatisch erkannt werden)
   - **Root Directory:** `apps/web`
   - **Build Command:** `cd ../.. && pnpm install --frozen-lockfile && pnpm --filter @research-hub/web build`
   - **Install Command:** `echo skipped`
   - **Output Directory:** `.next`
3. **Environment Variables** — alle setzen (Production + Preview):

```
NEXT_PUBLIC_SUPABASE_URL=https://zxpweqryywixicirxkwu.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<aus .env.local — der ANON JWT>
SUPABASE_SERVICE_ROLE_KEY=<aus credentials "supabase_knowledge_base">
RESEARCH_WORKER_URL=https://<railway-url-aus-schritt-5>
RESEARCH_WORKER_SECRET=<SELBER WERT wie WORKER_SHARED_SECRET in Railway — das ist kritisch!>
GOOGLE_SERVICE_ACCOUNT_JSON=<gleicher JSON-String wie im Worker — wird aktuell vom Web nur fürs Icon-Preview verwendet, kann später weg>
```

4. **Deploy**. Dauert ~3 min. Bei Erfolg: die `xxx.vercel.app` URL testen — Login-Page sollte erscheinen, Google-SSO sollte funktionieren (Login → landet im Dashboard mit leerer Job-Liste).

---

## 7. DNS: research subdomain

Domain-Provider von `ecomtorials.de` öffnen (nicht Cloudflare — laut Memory).

1. DNS-Einträge → **+ Add Record**
2. Type: **CNAME**
3. Host: `research`
4. Value: `cname.vercel-dns.com` (oder die von Vercel angezeigte Ziel-Domain unter Project → Settings → Domains → Add)
5. TTL: 300
6. Save
7. In Vercel: Project → Settings → Domains → **+ Add** → `research.ecomtorials.de` → **Add**. Vercel stellt SSL automatisch aus (Let's Encrypt, dauert 1-2 min).
8. Test: `https://research.ecomtorials.de` sollte direkt die Login-Page zeigen.

**Jetzt zurück zu Supabase** (Schritt 3 Site URL + Redirect URLs aktualisieren falls noch auf localhost):
- Site URL: `https://research.ecomtorials.de`
- Redirect URLs: `https://research.ecomtorials.de/auth/callback`

---

## 8. E2E-Test

1. Login mit deinem `@ecomtorials.de` Google-Account → landest im Dashboard.
2. Klick **+ Neue Research** → Kunde wählen (z.B. "NatuRise") → Modus **Full** → Angle eingeben → **Research starten**.
3. Job-Detail-Seite öffnet sich automatisch. Nach ~10s tickt `step0_scrape` auf running, dann succeeded. Danach R1a/R1b/R2/R3 parallel.
4. Nach ~25-30 min: Status = `succeeded`, Score ≥ 9.0, "Report ansehen" Button.
5. "Report ansehen" → gerenderte MD, "MD herunterladen" und "DOCX herunterladen" Buttons funktionieren.
6. Drive-Ordner des Kunden checken → Unterordner `Research 2026-04-xx - full - NatuRise/` mit `.md` + `.docx` drin.

**Budget-Warnung:** Ein Full-Run kostet ~$2.77. Teste zuerst mit `mode=custom` und nur `step0_scrape + assembly_export` angekreuzt (Kosten <$0.10), um die Infrastruktur zu verifizieren ohne die volle Pipeline zu zahlen.

---

## Troubleshooting

**Worker 401 "invalid signature":**
`WORKER_SHARED_SECRET` (Railway) und `RESEARCH_WORKER_SECRET` (Vercel) müssen identisch sein. Auch Whitespace-Unterschiede brechen HMAC.

**Worker startet nicht (Railway healthcheck fail):**
Logs checken: `MCP server failed to start` → vermutlich fehlt `ANTHROPIC_API_KEY` oder `PERPLEXITY_API_KEY`. Alle Keys müssen im Railway-Service gesetzt sein (nicht im GitHub-Repo!).

**Dashboard zeigt keine Kunden:**
`clients` Tabelle in `zxpweqryywixicirxkwu` muss Einträge haben. Live-Check:
```sql
SELECT id, name, drive_folder_id FROM clients ORDER BY name;
```

**Drive-Upload schlägt fehl:**
Service-Account hat keinen Zugriff auf den Kunden-Ordner. Ordner in Drive öffnen → **Teilen** → Service-Account-E-Mail als "Inhalt-Manager" einfügen.

**Google SSO "redirect_uri_mismatch":**
In der GCP OAuth-Config fehlt die exakte Callback-URL. Supabase will `https://zxpweqryywixicirxkwu.supabase.co/auth/v1/callback` (nicht `/auth/callback` — das ist unser App-Callback, nicht der von Supabase).
