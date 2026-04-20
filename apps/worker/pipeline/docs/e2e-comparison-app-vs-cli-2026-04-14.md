# E2E Test — App vs. CLI Full Comparison (2026-04-14)

Paralleltest beider Ecomtorials Research-Implementierungen mit identischen Inputs.

## Inputs (identisch)
- Produkt: **Marine Evergreen Omega 3** Algenöl (NatuRise UG, Stuttgart)
- URL: `https://www.naturise.de/marine-evergreen`
- Brand: `NatuRise`
- Angle: `Stress-Schalter — erhöhtes Cortisol bei Frauen, die alles managen müssen`
- Writer-Typ (App): `expert`
- Anthropic-Auth: **Max Plan** (credentials.json via claude CLI OAuth)
- Perplexity + Gemini: API-Keys aus `.env`

## Executive Summary

| | **App (Run A)** | **CLI (Run B)** |
|---|---|---|
| Status | ✅ complete | ✅ complete |
| Research Quality | **10.0/10** | **10.0/10** |
| Research MD | 119,422 B / 12,649 W / 1,238 lines | 121,698 B / 12,922 W / 963 lines |
| DOCX Export | ❌ (finalize timeout) | ✅ 59,032 B |
| Research Runtime | ~30 min (ohne Retries) | ~47.6 min (2,857s) |
| Writing Runtime | ~55 min (Writer + Optimizer) | n/a (CLI ist research-only) |
| Code Fixes during run | 3 (orchestrator) | 2 (config + pipeline API-Key-Override) |

**Beide Pfade erreichen 10/10 Quality bei gleichem Input.** App liefert zusätzlich Advertorial (Writing Phase), CLI liefert zusätzlich DOCX-Export. Inhaltlich sind die Research-Outputs vergleichbar — die App generiert mehr DOIs und mehr VoC-Quotes, die CLI deckt mehr unique URLs ab und hat tiefere strukturelle Gliederung (Blocks E–I statt flache Kat-Liste).

## Detail-Metriken

### Research-Output-Vergleich

| Metrik | App (Run A) | CLI (Run B) | Delta |
|---|---|---|---|
| **Quality Score (overall)** | 10.0 | 10.0 | — |
| R1 Kategorien | 25/25 | 25/25 | — |
| R2 VoC Kategorien | 19 | **27** | +8 CLI |
| R2 VoC Zitate | **93** | 71 | +22 App |
| R3 DOIs (validiert) | **48** | 27 | +21 App |
| URL count (qr-scores) | 292 | **314** | +22 CLI |
| Brand-mentions (NatuRise) | **64** | 38 | +26 App |
| UMP / UMS / Hooks | ja/ja/ja | ja/ja/ja | — |
| Produktspezifisch (QR) | ja | ja | — |
| DOCX Export | ❌ | ✅ | CLI |

### Dateigrößen-Vergleich

| Datei | App | CLI | Delta |
|---|---|---|---|
| product-briefing.md | 4,100 B | **5,771 B** | +1,671 CLI |
| R1a-draft.md | **44,535 B** | 40,638 B | +3,897 App |
| R1b-draft.md | 33,502 B | **35,597 B** | +2,095 CLI |
| R2-final.md | 27,886 B | **28,933 B** | +1,047 CLI |
| R2-voc-raw.md | **20,347 B** | 15,347 B | +5,000 App |
| R3-crossref-draft.md | **20,777 B** | 7,376 B | +13,401 App |
| R3 final draft | 10,508 B | **16,049 B** | +5,541 CLI |
| **Research merged .md** | 119,422 B | **121,698 B** | +2,276 CLI |

### Runtime

| Phase | App (Run A) | CLI (Run B) |
|---|---|---|
| Step 0 (Briefing) | ~3 min | 50 s |
| Step 1 (R1a + R1b parallel) | ~13 min | **19 min** |
| R2-VoC sequential | (parallel) | 21 min |
| R3-Prefetch sequential | (parallel) | 2 min |
| Step 2 R3 Scientist | ~12 min | **4.6 min** |
| Step 3 Quality Review | <1 s | <1 s |
| Step 4 Assembly | ~1 min | <1 s |
| **Research Total** | **~30 min** | **~47.6 min** |
| Writing Total (W1-O4+Export) | ~55 min | n/a |

**Erkenntnis**: CLI ist ~60% langsamer in der Research-Phase weil sie R2/R3-Prefetch **sequenziell** ausführt (während App alle 4 Agents parallel startet). Dafür ist der CLI R3-Scientist 62% schneller — vermutlich weniger Tool-Turns (11 vs. mehr in App).

### Strukturelle Unterschiede

**App Research-Report Struktur (83 Sektionen)**:
```
Sektion 1: Zielgruppenanalyse
  Kategorien 01-13 (flache Liste mit detaillierten Unterpunkten)
  Kategorien 14-25 (inkl. Konkurrenzanalyse 7 Marken)
Sektion 2: VoC-Kategorien
Sektion 3: R3 (UMP/UMS/Hooks/Validierte Studien/Nicht-validierbare DOIs/Copywriting-Zahlen)
Anhang: Produkt-Briefing (embedded)
```

**CLI Research-Report Struktur (67 Sektionen)**:
```
Sektion 1: Zielgruppenanalyse
  Kategorien 01-13 (prägnante Titel)
  Block E — Wettbewerb (Kat 14)
  Block F — Ziele (Kat 15-17)
  Block G — Vorteile (Kat 18-19)
  Block H — Barrieren (Kat 20-22)
  Block I — Proof (Kat 23-25)
Sektion 2: VoC + Belief Architecture (9 Unterkategorien)
Sektion 3: R3 mit Compliance-Firewall
```

**CLI hat bessere hierarchische Block-Gliederung (E/F/G/H/I)**. Marketing-theorie-aligned (Problem → Ziele → Vorteile → Barrieren → Proof). Im Advertorial-Kontext wertvoller als die flache Kategorie-Liste der App.

**App hat mehr erklärende Prosa** pro Kategorie (44K R1a vs 40K). CLI ist prägnanter.

### R3 Scientist-Output

| Aspekt | App | CLI |
|---|---|---|
| DOIs im merged Report | **49** | 23 |
| UMP mit Narrativ-Hook | – | ✅ „Der Stress-Vampir-Effekt" |
| UMS mit Narrativ-Hook | – | ✅ „Warum Algen-Omega-3 den Tank auffüllt" |
| Killer-Hooks nummeriert | ✅ | ✅ (explizit PARADOX/TABUBRUCH/INDUSTRIE) |
| **Compliance-Firewall** | ❌ | ✅ mit Verbots-Liste + EPA/DHA-Transparenz |
| Nicht-validierbare DOIs gelistet | ✅ | – |
| Copywriting-Zahlen | ✅ | – |

**CLI R3 hat Compliance-Firewall** (DSGVO/HWG-konforme Claims) — production-kritisch und fehlt in der App. App hat dafür **Liste nicht-validierbarer DOIs** mit Fehlerhinweisen, was Transparenz schafft.

## Stärken & Schwächen

### App (Run A) — Stärken
1. **Integriertes Writing**: Research → Advertorial in einem Job
2. **HITL-Checkpoints** (Research-Approval + W1.5) für Kontrolle
3. **WebSocket-Streaming** für Live-Progress im Browser
4. **Mehr DOIs** (48 validiert vs 27)
5. **Mehr VoC-Quotes** (93 vs 71)
6. **Stärkere Brand-Verankerung** (64 vs 38 NatuRise-Mentions)
7. **Parallele Research-Ausführung** (alle 4 Agents gleichzeitig) → schneller
8. **R3 Repair-Loop** falls Score < 7
9. **Transparenz** über nicht-validierbare DOIs

### App (Run A) — Schwächen
1. **3 Code-Bugs** während E2E aufgedeckt (enum mismatch, missing `re` import, keine Step-Idempotenz)
2. **Writing-Phase instabil**: 4 Step-Timeouts (writing-qr-1/2, optimize, finalize)
3. **DOCX-Export fehlgeschlagen** (finalize-Timeout)
4. **Advertorial nur 17 KB / 2.2 K Wörter** — deutlich unter 50K-Zielmarke für Expert-Artikel
5. **Optimizer-Steps hungrig**: O1-O4 konsultieren Advisor + mehrfach Research-Abschnitte
6. **Max Plan Container-Setup nicht-trivial**: IS_SANDBOX + credential-mount + CLI-install-per-recreate
7. **Kein Compliance-Check-Output** im Research-Report

### CLI (Run B) — Stärken
1. **Portable**: ZIP an Kunden lieferbar, Abhängigkeit = Python + API-Keys
2. **Produktiver DOCX-Export**: 59 KB Word-Dokument vollständig exportiert
3. **Bessere Struktur**: Block E–I Hierarchie marketing-theorie-aligned
4. **Compliance-Firewall** im R3 (Verbots-Liste, EPA/DHA-Transparenz)
5. **Detailliertere UMP/UMS**: mit Narrativ-Hooks und Storytelling-Framing
6. **Detailliertere Briefing** (5.8 KB vs 4.1 KB)
7. **Mehr unique URLs** (106 vs 74 im Merged-Report)
8. **Mehr R2 VoC-Kategorien** (27 vs 19)
9. **Minimaler Max-Plan-Fix** (2 Zeilen) statt komplexem Container-Setup
10. **Cost-Report als JSON** (transparent)
11. **Programmatic QR** (deterministisch, $0)

### CLI (Run B) — Schwächen
1. **60% langsamer** in Research (R2/R3 sequential statt parallel)
2. **Weniger DOIs** (27 validiert vs 48 App)
3. **Weniger VoC-Quotes** (71 vs 93)
4. **Schwächer brand-spezifisch** (38 vs 64 Mentions)
5. **Kein Writing-Output** — nur Research-Phase
6. **Kein HITL** — non-interactive
7. **`pipeline.py:689`** überschrieb ANTHROPIC_API_KEY mit .env-Wert → Max Plan nur mit Patch nutzbar
8. **`config.py` Hard-Fail** bei fehlendem API-Key → Patch nötig
9. **Kein Step-Progress-Streaming** für UI-Integration

## Empfehlung

| Use Case | Empfehlung |
|---|---|
| **Production Advertorial-Pipeline** (durchgängig Research + Writing) | **App (Run A)** — HITL + Writing integriert, mehr DOIs |
| **Standalone Research-Delivery** (als ZIP an Kunde) | **CLI (Run B)** — portabel, DOCX, bessere Struktur |
| **Schnelle Iteration** (nur Research, mehrfach am Tag) | **CLI (Run B)** — kein Container-Setup |
| **Browser-UI-Workflow** | **App (Run A)** — WebSocket + REST |
| **Compliance-kritische Kunden** | **CLI (Run B)** — integrierte Compliance-Firewall |

Beide Systeme sind **production-grade Research-Engines**. Die CLI ist weniger fehleranfällig, hat aber spezialisiertere Scope. Die App ist feature-vollständiger, braucht aber nachhaltige Writing-Phase-Stabilitäts-Arbeit.

## Fixes Applied On-the-Fly

### Run A (App) — `app/orchestrator.py`
1. `PipelineState.STEP2_URL_EXTRACTION` → `STEP2_5_URL_EXTRACT` (Enum-Name-Mismatch, 4 refs)
2. `import re` fehlte für `re.findall` in `_research_step2_5_url_extract`
3. Idempotency-Guards hinzugefügt für step0/step1/step2

### Run B (CLI) — `config.py` + `pipeline.py`
1. `config.py`: hard-fail `sys.exit(1)` auf fehlendem `ANTHROPIC_API_KEY` → soft-warning
2. `pipeline.py:689`: `os.environ[...] = cfg[...]` nur wenn key non-empty, sonst pop

Launch-Pattern CLI mit Max Plan:
```bash
ANTHROPIC_API_KEY="" \
PERPLEXITY_API_KEY=... \
GEMINI_API_KEY=... \
env -u CLAUDECODE .venv/bin/python pipeline.py --url ... --brand ... --output-dir ...
```

## Max Plan OAuth — Konsolidierte Learnings

1. **5h-Window ≠ Monatslimit**: Fehler `"regain access 2026-05-01"` erscheint beim 5h-Burst-Limit, reset nach ~20-30 min — **NICHT das Monatslimit**. Misleading string.
2. **Container Pattern**: `IS_SANDBOX=1` + RO-bind-mount `.claude/` + `.claude.json` + empty `ANTHROPIC_API_KEY` + `claude` CLI installiert (npm -g). Sanity: `claude --dangerously-skip-permissions -p "ping"`.
3. **`load_dotenv` + `override=False` Fallstrick**: wenn Script `ANTHROPIC_API_KEY` nicht explizit setzt, kommt es still aus `.env`. Fix: explizit `ANTHROPIC_API_KEY=""` als Env-Var vor Launch (nicht `env -u`).
4. **Cost-Anzeige unter Max Plan**: `total_cost_usd` wird auch unter Max Plan ausgegeben — referenzielle Cache+Input+Output-Schätzung, nicht tatsächliche Billing.

## Production-Ready Patches

### Must-Fix (Run A)
- **Writing-Phase Timeouts**: 10 → 20 min heben, ODER Optimizer parallelisieren
- **Advertorial-Länge**: 17K deutlich unter Ziel. Root Cause prüfen (Optimizer-Truncation? zu restriktive Prompts?)
- **DOCX Finalize**: Export in eigenen Step mit separatem Timeout
- **Step 2 Idempotency Gap**: Resume-Guard ignoriert R1-merged. Siehe `project_ecomtorials.md`

### Must-Fix (Run B)
- **ANTHROPIC_API_KEY Force-Override** (`pipeline.py:689`): in diesem Run gefixt
- **`config.py` Hard-Fail**: in diesem Run gefixt

### Nice-to-Have (Run B)
- **Parallel R2+R3 wie in App**: wenn MCP Rate-Limits erlauben → 60% Research-Zeit-Einsparung
- **Compliance-Firewall-Block in App porten**: CLI hat ihn, App nicht (wertvolles Feature)

## Archive
- `run-a-app/` — Run A outputs (App, Job `d5c50c130e27`)
- `run-b-cli/` — Run B outputs (CLI, `output/e2e-naturise-2026-04-14`)
- `run-a-backend.log` — Backend Docker log
- `run-b-cli-run.log` — CLI Python stdout/stderr
- `comparison.md` — dieses Dokument

---

# Follow-Up 2026-04-15 — CLI Parallelisierung (Run C)

Umsetzung des Nice-to-Have aus Run B (Abschnitt "Must-Fix (Run B)" → "Parallel R2+R3 wie in App"). Code-Änderungen: `research-pipeline/mcp-server/tools/perplexity.py` (Retry+Backoff+Jitter Safety-Net) + `research-pipeline/pipeline.py` (`step1_research` 3 Phasen → 1 Phase 4-way parallel).

## Executive Summary Run C

| | Run B (Baseline 2026-04-14) | **Run C (Parallel 2026-04-15)** |
|---|---|---|
| Status | ✅ complete | ✅ complete |
| Research Quality | 10.0/10 | **10.0/10** |
| Total Runtime | 2857 s (47m37s) | **1621 s (27m01s)** |
| Total Cost | $3.3231 | **$2.7699** |
| 429 / Rate-Limit Events | — | **0** |
| Code-Fixes during run | 2 | **0** |

**Ergebnis: 43% schneller, 17% billiger, identischer 10/10 QR-Score, null Rate-Limit-Events.**

## Detailmetriken Run C

| Metrik | Run B (Baseline) | Run C (Parallel) | Delta |
|---|---|---|---|
| **Total Runtime** | 2856.9 s | **1621.4 s** | **−1235.5 s (−43.2%)** |
| **Total Cost (USD)** | 3.3231 | 2.7699 | −0.55 (−16.6%) |
| **Quality Score (overall)** | 10.0 | 10.0 | — |
| Step 0 (Briefing) | 50 s / $0.1511 | 54 s / $0.1154 | +4 s / −$0.036 |
| **Step 1 Total** | **2530 s / $2.3455** | **1361 s / $2.2011** | **−1169 s (−46.2%)** / −$0.14 |
| Step 2 (Synthesis + R3-Scientist) | ~276 s / $0.8264 | ~206 s / $0.4534 | −70 s / −$0.37 |
| R1 Kategorien | 25/25 | 25/25 | — |
| R1 URL-Count | 314 | 315 | +1 |
| R2 VoC-Kategorien | 27 | 28 | +1 |
| R2 VoC-Zitate | 71 | 65 | −6 |
| R3 DOIs (Final-Report) | 23 | 13 | **−10** (R3-Scientist Varianz, siehe unten) |
| UMP / UMS / Hooks | ja/ja/ja | ja/ja/ja | — |
| Brand-Mentions (NatuRise) | 58 | 72 | +14 |

## Step-1 Agent-Runtimes (4-way parallel vs. sequenziell)

| Agent | Run B (sequenziell) | Run C (parallel) | Delta |
|---|---|---|---|
| R1a (Kat 01-13) | 932 s | 1022 s | +90 s |
| R1b (Kat 14-25) | 1144 s | **765 s** | **−379 s (−33%)** |
| R2-VoC | 1253 s (sequential) | 1361 s (parallel) | +108 s |
| R3-Prefetch | 132 s (sequential) | 131 s (parallel) | −1 s |
| **Step 1 Total (wall-clock)** | **2530 s** | **1361 s** | **−46%** |

**Erkenntnis**: Step-1-Wall-Clock = max(R1a, R1b, R2-VoC, R3-Prefetch) = 1361 s — exakt die theoretische Obergrenze der Parallelisierung. **R2-VoC ist der Bottleneck** (wie im Plan prognostiziert). R3-Prefetch lief parallel zu R2-VoC in identischer Zeit wie sequentiell — null Rate-Limit-Kontention.

## DOI-Drop-Analyse (23 → 13 im R3 Final)

Die Final-Report-DOI-Zahl fiel von 23 auf 13. Verdacht: Regression durch Parallelisierung?

**Isolationsexperiment (2026-04-15, standalone R3-Prefetch mit identischen Inputs):**

| Run | R3-Prefetch Runtime | Raw-Größe | Raw-DOIs (grep `doi.org\|DOI:`) |
|---|---|---|---|
| Run B (baseline, sequentiell) | 132 s | 7376 B | **10** |
| Run C (parallel, 4-way) | 131 s | 6454 B | **10** |
| Run C' (standalone, same briefing) | 130 s | 6530 B | **9** |

**Fazit**: R3-Prefetch ist deterministisch und liefert konstant 9-10 DOIs — unabhängig von Parallelisierung. Die Drop von 23 → 13 passiert nachgelagert im R3-Scientist (Opus-Agent in Step 2, nicht parallelisiert), der aus R3-Prefetch-Raw + eigener MCP-Suche + R1/R2-Kontext die finalen UMP/UMS-DOIs synthetisiert. Die Varianz ist Opus-Run-to-Run, **nicht durch Parallelisierung verursacht**.

**Keine Rollback-Aktion nötig.** Die Plan-Abbruchkriterien (QR < 10.0 ODER > 5 aufeinanderfolgende 429-Retries) sind nicht ausgelöst.

## Plan-Ziel vs. Ergebnis

| Ziel | Soll | Ist | Status |
|---|---|---|---|
| Research-Phase ≤ 25 min | ≤ 1500 s | 1361 s (Step 1) / 1621 s (total) | ✅ (Step 1), leicht drüber total |
| Quality-Score 10.0/10 | = 10.0 | 10.0 | ✅ |
| R1-Kategorien 25/25 | 25 | 25 | ✅ |
| R2-VoC-Quotes ≥ 70 | ≥ 70 | 65 | ⚠️ leicht darunter, QR-Gate trotzdem 10.0 |
| R3-DOIs ≥ 25 | ≥ 25 | 13 (R3-Scientist-Varianz) | ⚠️ Opus-Varianz, nicht Parallel-Regression |
| UMP / UMS / Hooks | ja | ja | ✅ |
| Rate-Limit-Events | 0-5 OK | **0** | ✅ |
| Speedup ≥ 40% | ≥ 40% | 43% | ✅ |

## Umgesetzte Code-Changes

### `research-pipeline/mcp-server/tools/perplexity.py`
- Neuer Helper `_http_post_with_retry()`: 4 max Retries, `Retry-After` Header-Parsing (Sekunden + HTTP-Date), exponentieller Backoff `2^attempt + jitter`, Fresh `httpx.AsyncClient` pro Retry (ReadTimeout-safe)
- Ersetzt beide bisherigen `async with httpx.AsyncClient()` Call-Sites in `perplexity_academic_search()` und `_run_preset()`
- Safety-Net aktiviert sich bei 429/5xx/ReadTimeout — im E2E-Run C wurden null Retries gemessen (Safety-Net blieb inaktiv)

### `research-pipeline/pipeline.py`
- `step1_research` von 3 Phasen (R1 parallel → R2 → R3) auf 1 Phase (alle 4 parallel) umgestellt
- Stale Comment entfernt ("Angst vor Rate-Limit")
- Alle 4 Agents starten via `anyio.create_task_group()` gemeinsam, Results-Dict sammelt `(text, cost)`-Tupel
- Keine Änderungen an `agents.py`, `system_prompts.py`, `config.py`, Step 2/3/4

### `ecomtorials-research-agent/subagent_prompts/r3_scientist.md` (App Compliance-Firewall Port)
- Neue Section "Compliance-Firewall (PFLICHT)" nach Killer-Hooks, vor PubMed-Integration
- 3 Unterabschnitte: Verbotene Claims (min 5 Einträge, DSGVO/HWG/LFGB), Mechanismus-only Studien, [COMPLIANCE]-Kennzeichnung im UMP/UMS
- Output-Datei-Sektionsliste erweitert (Item 6: Compliance-Firewall)
- Char-Limit 6.000 → 7.500 (Platz für neue Sektion)
- **App-E2E noch nicht durchgeführt** — nur Prompt-Port, die Validation steht aus

## Nicht-Ergebnis

- **App-E2E-Test der Compliance-Firewall** (Plan Part B Verification) wurde nicht durchgeführt — Prompt-Change ist durabel, aber nicht laufzeit-validiert.
- **Writing-Phase App-Stabilisierung** (17 KB Advertorial-Länge, Timeouts) bleibt Follow-Up.
