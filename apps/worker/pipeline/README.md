# Ecomtorials Research Pipeline

Eigenstaendige, portable Python SDK Pipeline fuer D2C Marketing-Research.
Produziert vollstaendige Research-Reports (120K+ chars, 25 Kategorien, 300+ Quellen) als MD + DOCX.

**Version 2026-04-15 (Production Ready)** — 4-way parallele Research-Phase (R1a + R1b + R2-VoC + R3-Prefetch),
Retry+Backoff Safety-Net am Perplexity-Tool, Compliance-Firewall im R3-Output.
Vollstaendiger E2E-Vergleich mit der App-Variante: [`docs/e2e-comparison-app-vs-cli-2026-04-14.md`](docs/e2e-comparison-app-vs-cli-2026-04-14.md).

| Kennzahl | Wert |
|---|---|
| Research-Runtime (NatuRise Benchmark) | **~27 Minuten** |
| Research-Kosten (NatuRise Benchmark) | **~$2.77** |
| Quality Score | **10/10** |
| Rate-Limit-Events im E2E | **0** |

---

## Schritt-fuer-Schritt Setup (neuer PC)

### 1. Voraussetzungen

- **Python 3.11+** — `python3 --version`
- **Node.js 18+** — `node --version` (fuer DOCX-Export)
- **Claude Code CLI** — `npm install -g @anthropic-ai/claude-code` (wird vom SDK benoetigt)

### 2. ZIP entpacken

```bash
unzip ecomtorials-research-pipeline.zip
cd ecomtorials-research-pipeline
```

### 3. Python-Dependencies installieren

```bash
pip install -r requirements.txt
```

Dies installiert: `claude-agent-sdk`, `anyio`, `python-dotenv`, `httpx`, `mcp`

### 4. Node.js-Dependencies installieren (fuer DOCX-Export)

```bash
npm install
```

### 5. API-Keys konfigurieren

```bash
cp .env.example .env
```

Dann `.env` editieren und alle Keys eintragen:

```env
# PFLICHT — Claude API
ANTHROPIC_API_KEY=sk-ant-...

# PFLICHT — Perplexity (fuer Web-Recherche)
PERPLEXITY_API_KEY=pplx-...

# EMPFOHLEN — Gemini (Google Search Grounding, erweiterte Recherche)
GEMINI_API_KEY=AIza...

# EMPFOHLEN — CrossRef (kostenlos, eigene Email reicht)
CROSSREF_EMAIL=your@email.com

# OPTIONAL — PubMed (kostenlos, verbessert Rate Limits)
NCBI_API_KEY=
```

**Wo bekomme ich die Keys?**

| Key | Registrierung | Kosten |
|-----|---------------|--------|
| ANTHROPIC_API_KEY | [console.anthropic.com](https://console.anthropic.com) | Pay-per-use (~$3/Report) |
| PERPLEXITY_API_KEY | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) | Pay-per-use |
| GEMINI_API_KEY | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Kostenlos (Free Tier) |
| CROSSREF_EMAIL | Keine Registrierung — einfach E-Mail angeben | Kostenlos |
| NCBI_API_KEY | [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/settings/) | Kostenlos |

### 6. MCP-Server venv erstellen (einmalig)

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows
pip install -r requirements.txt
deactivate
cd ..
```

### 7. Pipeline starten

```bash
python3 pipeline.py \
  --url "https://www.example.com/produkt" \
  --brand "MeinBrand" \
  --angle "Hauptthema fuer den Advertorial-Angle"
```

### 8. Ergebnis pruefen

```
output/MeinBrand-2026-04-02/
├── Research-MeinBrand-2026-04-02.md      # Vollstaendiger Report (120K+ chars)
├── Research-MeinBrand-2026-04-02.docx    # Word-Export
├── product-briefing.md                    # Produkt-Analyse
├── R1a-MeinBrand-draft.md                 # Zielgruppe Kat 01-13
├── R1b-MeinBrand-draft.md                 # Zielgruppe Kat 14-25
├── R2-MeinBrand-voc-raw.md                # Echte Kundenzitate
├── R2-MeinBrand-final.md                  # Belief Architecture
├── R3-crossref-MeinBrand.md               # Validierte Studien
├── R3-MeinBrand-final.md                  # UMP/UMS Mechanismus
├── qr-scores.json                         # Quality Scores
└── cost-report.json                       # Kosten pro Step
```

---

## Alle CLI-Optionen

```bash
python3 pipeline.py \
  --url "https://..."           # Pflicht: Produkt-URL
  --brand "BrandName"           # Pflicht: Markenname
  --angle "Thema"               # Optional: Research-Angle (Default: generisch)
  --product-name "Produkt XY"   # Optional: Produktname (Default: Brand)
  --output-dir ./output/custom  # Optional: Output-Verzeichnis
```

---

## Was der Report enthaelt

| Sektion | Inhalt | Quellen |
|---------|--------|---------|
| **1. Zielgruppenanalyse** | 25 Kategorien: Demografie, Psychografie, Schmerzpunkte, Loesungen, Wettbewerb, Barrieren, Proof | 200+ URLs |
| **2. Voice of Customer** | Echte Kundenzitate (Foren, Reddit, Trustpilot), Belief Breaks, Skeptiker-Argumente | 40+ Zitate |
| **3. UMP/UMS + Studien** | Unique Mechanism of Problem/Solution, DOI-validierte Studien, Killer-Hooks, Compliance | 10+ DOIs |

## Qualitätsicherung

Die Pipeline hat ein eingebautes **Quality Review + Repair System**:

1. **Programmatischer QR** — prüft automatisch nach jedem Run: Kategorien-Vollständigkeit, URL-Anzahl, VoC-Zitate, DOI-Anzahl, UMP/UMS-Präsenz, Killer-Hooks, Produktspezifität
2. **Gezielter Repair-Loop** — wenn der QR-Score unter 7.0 fällt, wird automatisch der schwächste Agent nochmal mit einem spezifischen Reparatur-Prompt aufgerufen (z.B. fehlende Kategorien nachrecherchieren oder zusätzliche DOIs finden)
3. **Step 0 Validation Gate** — wenn die Produkt-URL nicht erreichbar oder leer ist, bricht die Pipeline ab bevor Kosten entstehen

Der Repair-Loop läuft maximal 1x und ist budgetiert ($0.50-$1.50 je nach Reparatur-Typ).

---

## Benchmarks & Tests

Die Pipeline umfasst schnelle und kostengünstige Unit-Tests für die Quality-Review-Logik:

| Type | Datei | Tests | Dauer | Kosten |
|------|-------|-------|-------|--------|
| Quality | `app/tests/test_quality_benchmark.py` | 4 | ~0.12s | $0 |
| Pipeline | `app/tests/test_pipeline_benchmark.py` | 7 | ~0.12s | $0 |

**Total:** 59 Tests, ~0.3s Laufzeit, $0

Siehe `BENCHMARK.md` für detaillierte Dokumentation.

---

## Ordner-Struktur

```
ecomtorials-research-pipeline/
├── pipeline.py              # Hauptorchestrator + CLI
├── agents.py                # drain_query() + SDK-Konfiguration
├── system_prompts.py        # Optimierte Agent-Prompts (R1/R2/R3)
├── synthesis.py             # Programmatische R2-Synthese + Report-Assembly
├── config.py                # .env Loading + Pfade + Budgets
├── tools.py                 # MCP-Server Konfiguration
├── prompts.py               # Prompt-Loader fuer .md Dateien
├── export.py                # MD → DOCX/PDF Export
├── export-docx.mjs          # Node.js DOCX-Konverter
├── package.json             # Node.js Dependencies
├── requirements.txt         # Python Dependencies
├── .env.example             # API-Key Template
├── mcp-server/              # Perplexity + CrossRef + PubMed Tools
│   ├── server.py            # FastMCP Server (8 Tools)
│   ├── config.py            # Kategorien, Thresholds, Blocked Domains
│   ├── requirements.txt     # MCP-Server Dependencies
│   └── tools/               # API-Wrapper
│       ├── perplexity.py    # 4 Perplexity-Presets
│       ├── crossref.py      # CrossRef DOI-Suche + Validierung
│       └── pubmed.py        # PubMed Literatursuche
├── research-prompts/        # Research-Prompt-Dateien (.md)
├── agents/                  # Quality-Reviewer Definition
└── output/                  # Generierte Reports
```
