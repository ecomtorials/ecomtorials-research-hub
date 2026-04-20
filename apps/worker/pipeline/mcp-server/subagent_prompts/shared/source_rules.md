# Source Rules (Shared — referenziert von R1, R2, R3)

## URL-Erfassungsregel

Bei JEDEM WebSearch- oder Perplexity-Ergebnis:
1. **URL sofort extrahieren** — die direkte URL aus dem Suchergebnis, NICHT die Domain
2. **URL-Format**: Immer vollständig mit `https://` — z.B. `https://www.gutefrage.net/frage/lyocell-bettwaesche-schweiss`
3. **Inline-Quellenformat**: `– [Kurzname](URL)` — z.B. `– [gutefrage.net](https://www.gutefrage.net/frage/lyocell-bettwaesche-schweiss)`

## Entscheidungsregeln

| Quelle | URL-Format | Beispiel |
|--------|-----------|---------|
| WebSearch-Ergebnis | Direkte URL aus Suchergebnis | `[heimeule.de](https://heimeule.de/lyocell-bettwaesche-test/)` |
| Perplexity-Ergebnis | Echte Quell-URL aus Perplexity-Fußnoten extrahieren (PFLICHT) | `[heimeule.de](https://heimeule.de/reizdarm-ernaehrung/)` |
| Forum/Reddit/gutefrage | Direkte Thread-URL | `[gutefrage.net](https://www.gutefrage.net/frage/bettwaesche-schweiss)` |
| Trustpilot/Amazon Review | Review-Seiten-URL | `[Trustpilot](https://de.trustpilot.com/review/twentythree.de)` |
| Wissenschaftliche Studie | DOI als vollständige URL | `[Kim 2021](https://doi.org/10.3390/ma14206205)` |
| Produktseite | Direkte Produkt-URL | `[twentythree.de](https://twentythree.de/products/...)` |
| Keine URL verfügbar | [nicht verifiziert]-Tag | `– [nicht verifiziert]` |

## Fallback-Hierarchie

1. Direkte URL aus Tool-Ergebnis → verwenden
2. **Perplexity-Fußnoten-URL**: Fußnoten [1][2]... mit echten Quell-URLs → extrahieren
3. URL rekonstruierbar (Domain + Pfad sichtbar) → rekonstruieren mit `https://`
4. Nur Domain bekannt → `[DOMAIN-ONLY: domain.de]`-Tag setzen
5. Perplexity-Ergebnis OHNE Fußnoten-URLs → `[PERPLEXITY-OHNE-URL]`-Tag setzen → WebSearch Follow-up PFLICHT
6. Gar keine Quelle → `[nicht verifiziert]`

## URL-Integritätsregeln (PFLICHT — gilt für ALLE Agents, v3.5)

### Das Kernproblem: Pfad-Halluzination
LLMs halluzinieren URLs nicht als ganze Domains — sie kennen echte Domains. Das Problem: Sie KONSTRUIEREN plausible URL-Pfade die nicht existieren.
Beispiel: `simone-weiss.de` existiert — aber `/frauengesundheit/wie-omega-3-mir-geholfen-hat-mein-weg-raus-aus-stillen-entzuendungen/` ist erfunden.
Beispiel: `symptome.ch` existiert — aber `/threads/omega-3-fettsaeuren-mangel-erfahrung.129764/` hat eine erfundene Thread-ID.

### Regeln
1. **Copy-Paste-Only**: Jede URL MUSS 1:1 aus einem Tool-Ergebnis kopiert werden. URL-Pfade NIEMALS "aus dem Wissen" rekonstruieren, auch nicht teilweise. Ein einziges geändertes Pfad-Segment macht die URL ungültig.
2. **Bei Unsicherheit**: `[DOMAIN-ONLY: domain.de]`-Tag statt konstruiertem Pfad. Der Orchestrator repariert per WebSearch in Step 4a.
3. **Forum-Thread-IDs**: IMMER aus dem Tool-Ergebnis kopieren, NIEMALS ausdenken.
4. **Blog-Slugs**: Pfade wie `/blog/mein-toller-artikel/` NIEMALS rekonstruieren.
5. **Recycling-Limit**: Max 3× dieselbe URL für verschiedene Claims. Dann: eigene Quellen oder `[nicht verifiziert]`.

### PMC/PubMed-URLs
PMC-IDs und PubMed-IDs NICHT aus dem Gedächtnis. NUR aus Tool-Ergebnissen (WebSearch, Perplexity, pubmed_search).
Eine PMC-URL für 3+ verschiedene Claims = HALLUZINATIONSVERDACHT.

## Domain-Authority-Tiers (PFLICHT — gilt für R1 und R2)

Jede nicht-DOI-Quelle muss einem Authority-Tier zugeordnet werden. Tier bestimmt, welche Claims die Quelle belegen darf. Die Zuordnung ist **branchenabhängig** — leite die passenden Tier-A/B-Domains aus `{{PRODUKTKATEGORIE}}` und `{{INDUSTRY_CONTEXT}}` ab.

| Tier | Domain-Typ | Akzeptabel für |
|------|-----------|----------------|
| A | Fachportale, Institutionen, Testmagazine, Behörden | Alle Claims |
| B | Nischen-Fachblogs mit erkennbarer Redaktion | Branchenspezifische Claims |
| C | Brand-eigene Seiten | NUR Produktdaten (Preis, INCI/Inhaltsstoffe, Varianten) |
| D | Foren, Review-Plattformen (Trusted Platforms) | NUR VoC-Zitate + Erfahrungsberichte |
| E | Lifestyle-Blogs, generische Ratgeber | NUR als Kontext-Illustration mit [WEAK]-Tag |

### Tier A/B Beispiele nach Branche (NICHT abschließend — Agent leitet weitere ab)

| Branche | Tier A (Fachportale/Institutionen) | Tier B (Nischen-Fachblogs) |
|---------|-----------------------------------|---------------------------|
| Skincare/Kosmetik | derma.plus, hautarzt.de, pharmazeutische-zeitung.de, bfr.bund.de | skincareinsider.de, codecheck.info, beautypedia.com, inci.de |
| Supplements/Health | examine.com, pharmazeutische-zeitung.de, verbraucherzentrale.de, efsa.europa.eu | medizin-transparent.at, gesundheit.gv.at, ndr.de/ratgeber/gesundheit |
| Textil/Home | oeko-tex.com, testfabrics.org, hohenstein.de | utopia.de, bewusst-haushalten.at, schlafwissen.com |
| Food/Ernährung | dge.de, bfr.bund.de, bzfe.de, efsa.europa.eu | eatsmarter.de, ernaehrungs-umschau.de |
| **Alle Branchen** | stiftung-warentest.de, oekotest.de, verbraucherzentrale.de, ncbi.nlm.nih.gov | utopia.de, medizin-transparent.at |

**Ableitung**: Wenn die Produktkategorie NICHT in der Tabelle steht, identifiziere die 3-5 relevantesten Fachportale durch eine WebSearch: `"[Produktkategorie] Fachportal Test Bewertung .de"`. Lifestyle-Portale (wunderweib.de, brigitte.de, fit-for-fun.de, bild.de) sind IMMER Tier E.

### Domain-Mismatch-Regeln (PFLICHT)
- **Branchenfremd = VERBOTEN**: Wenn Domain NICHT zur Produktkategorie passt → NICHT verwenden. Döner-Blog für Skincare = VERBOTEN. Fitness-Blog für Textil = VERBOTEN. Skincare-Blog für Supplements = PRÜFEN (verwandt aber nicht identisch).
- **Tier E für faktenbasierte Claims = VERBOTEN**: Lifestyle-Blog darf NICHT als Beleg für wissenschaftliche, medizinische oder technische Aussagen dienen
- **Tier C als allgemeine Quelle = VERBOTEN**: Marken-eigene Seiten belegen NUR Produkt-Fakten, nicht allgemeine Claims über die Branche
- **Konkurrenz-Produktseiten**: NUR in Kat. 14 (Konkurrenz-Claims) erlaubt, NIRGENDWO sonst

### Inline-Validierung (PFLICHT für R1 und R2)
Bevor du eine URL als Quelle einsetzt, prüfe:
1. **Domain-Check**: Passt die Domain zur Produktkategorie? (Skincare → Dermatologie/Kosmetik | Supplements → Ernährungswissenschaft/Pharmazie | Textil → Materialwissenschaft/Zertifizierung | Food → Ernährungswissenschaft/Lebensmittelsicherheit)
2. **Tier-Check**: Ist der Authority-Tier ausreichend für den Claim-Typ?
3. **Im Zweifel**: `[nicht verifiziert]` ist IMMER besser als eine falsche Quelle

## Perplexity-Quellen-Extraktionsregel (PFLICHT)

Perplexity ist ein Recherche-WERKZEUG, nicht eine QUELLE.

**PFLICHT-Workflow bei jedem Perplexity-Ergebnis:**
1. Fußnoten-URLs in der Perplexity-Antwort identifizieren ([1] URL, [2] URL, ...)
2. Jede Aussage der passenden Fußnoten-URL zuordnen
3. Die echte URL als Inline-Quelle verwenden: `[Kurzname](URL)`
4. Wenn KEINE Fußnoten-URLs vorhanden: `[PERPLEXITY-OHNE-URL]`-Tag setzen → WebSearch Follow-up

**VERBOTEN:**
- `[Perplexity Pro]` oder `[Perplexity Pro: ...]` als Quellenangabe
- `(perplexity-result)` als URL
- Jede Quellenangabe die "Perplexity" als Quellennamen verwendet

**Max 3 `[PERPLEXITY-OHNE-URL]`-Tags** pro R-Step erlaubt.

## Quellenverzeichnis-Format

```
### Quellenverzeichnis
1. [Kurzname](https://vollständige-url) — Kontext
2. [Autor (Jahr)](https://doi.org/10.xxxx) — Titel. Journal.
```

## Review-Validierung

### Tags
- **[SYNTHETIC]**: Review ohne verifizierbare Quelle
- **[WRONG-PRODUCT]**: Review beschreibt offensichtlich anderes Produkt
- **[MANUFACTURER]**: Produktbeschreibung statt echte Kundenstimme

### Trusted Review Platforms
amazon.de, amazon.com, trustpilot.com, reddit.com, gutefrage.net, idealo.de, geizhals.de, testberichte.de, beautypedia.com, inci.de, gesundheitsfrage.net

## Study Tier System

| Tier | Beschreibung | Tag |
|------|-------------|-----|
| TIER 1 | RCTs in Top-Journals (Lancet, NEJM, JAMA, BMJ, Cochrane) | — |
| TIER 2 | Prospektive Studien, Meta-Analysen | — |
| TIER 3 | Observationsstudien, Kohortenstudien | — |
| TIER 4 | In-vitro, Tierstudien | [EXTRAPOLATION] |
| TIER 5 | Expertenmeinung, Herstellerstudien | [WEAK SOURCE] |

## PMID-Verbot

NIEMALS PMIDs angeben — nur DOI-Nummern (Format: `10.xxxx/xxxxx`).
Studien ohne validierten DOI: nur Autor + Jahr + Journal zitieren, OHNE Identifikator.
