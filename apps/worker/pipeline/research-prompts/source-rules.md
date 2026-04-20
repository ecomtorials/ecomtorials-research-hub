# Source Rules (referenziert von R1, R2, R3)

## URL-Erfassungsregel

Bei JEDEM WebSearch- oder Perplexity-Ergebnis:
1. **URL sofort extrahieren** — die direkte URL aus dem Suchergebnis, NICHT die Domain
2. **URL-Format**: Immer vollstaendig mit `https://` — z.B. `https://www.gutefrage.net/frage/lyocell-bettwaesche-schweiss`
3. **Inline-Quellenformat**: `– [Kurzname](URL)` — z.B. `– [gutefrage.net](https://www.gutefrage.net/frage/lyocell-bettwaesche-schweiss)`

## Entscheidungsregeln

| Quelle | URL-Format | Beispiel |
|--------|-----------|---------|
| WebSearch-Ergebnis | Direkte URL aus Suchergebnis | `[heimeule.de](https://heimeule.de/lyocell-bettwaesche-test/)` |
| Perplexity-Ergebnis | Echte Quell-URL aus Perplexity-Fussnoten extrahieren (PFLICHT) | `[heimeule.de](https://heimeule.de/reizdarm-ernaehrung/)` — die URL aus Perplexitys [1][2]... Fussnoten verwenden |
| Forum/Reddit/gutefrage | Direkte Thread-URL | `[gutefrage.net](https://www.gutefrage.net/frage/bettwaesche-schweiss)` |
| Trustpilot/Amazon Review | Review-Seiten-URL (nicht Einzel-Review) | `[Trustpilot](https://de.trustpilot.com/review/twentythree.de)` |
| Wissenschaftliche Studie | DOI als vollstaendige URL | `[Kim 2021](https://doi.org/10.3390/ma14206205)` |
| Produktseite | Direkte Produkt-URL | `[twentythree.de](https://twentythree.de/products/...)` |
| Keine URL verfuegbar | [nicht verifiziert]-Tag | `– [nicht verifiziert]` |

## Fallback-Hierarchie

1. Direkte URL aus Tool-Ergebnis → verwenden
2. **Perplexity-Fussnoten-URL**: Perplexity-Antworten enthalten Fussnoten [1][2]... mit echten Quell-URLs → diese extrahieren und als Inline-Quelle verwenden
3. URL rekonstruierbar (Domain + Pfad sichtbar) → rekonstruieren mit `https://`
4. Nur Domain bekannt → `[DOMAIN-ONLY: domain.de]`-Tag setzen, in Repair Gate nachrecherchieren
5. Perplexity-Ergebnis OHNE Fussnoten-URLs → `[PERPLEXITY-OHNE-URL]`-Tag setzen → WebSearch Follow-up PFLICHT (gleiche Aussage als Query)
6. Gar keine Quelle → `[nicht verifiziert]`

## Perplexity-Quellen-Extraktionsregel (PFLICHT)

Perplexity ist ein Recherche-WERKZEUG, nicht eine QUELLE. Die echten Quellen sind die Websites/Studien, die Perplexity in seinen Fussnoten [1][2]... zitiert.

**PFLICHT-Workflow bei jedem Perplexity-Ergebnis:**
1. Fussnoten-URLs in der Perplexity-Antwort identifizieren ([1] URL, [2] URL, ...)
2. Jede Aussage der passenden Fussnoten-URL zuordnen
3. Die echte URL als Inline-Quelle verwenden: `[Kurzname](URL)`
4. Wenn KEINE Fussnoten-URLs vorhanden: `[PERPLEXITY-OHNE-URL]`-Tag setzen → WebSearch Follow-up mit der Aussage als Query

**VERBOTEN — folgende Quellen-Formate sind NICHT erlaubt:**
- `[Perplexity Pro]` oder `[Perplexity Pro: Consumer Behavior]` oder aehnliche Varianten
- `(perplexity-result)` als URL
- `[Perplexity fast_search]`, `[Perplexity academic_search]` etc. als Quelle
- Jede Quellenangabe die "Perplexity" als Quellennamen verwendet

**Max 3 `[PERPLEXITY-OHNE-URL]`-Tags** pro R-Step erlaubt. Bei mehr: WebSearch Follow-up erzwingen.

## Quellenverzeichnis-Format (am Ende jedes R-Steps)

```
### Quellenverzeichnis
1. [Kurzname](https://vollstaendige-url) — Kontext (was wurde entnommen)
2. [Autor (Jahr)](https://doi.org/10.xxxx) — Titel. Journal.
```

Jede URL im Quellenverzeichnis muss eine direkte, klickbare URL sein. Keine nackten Domains.

## Review-Validierung

### Tags
- **[SYNTHETIC]**: Review ohne verifizierbare Quelle (keine echte URL, kein bekannter Review-Domain). Auch bei Placeholder-URL-Mustern: `/dp/B0[A-Z0-9]{7,10}`, `/comments/[a-z0-9]+/`, `example.com`
- **[WRONG-PRODUCT]**: Review beschreibt offensichtlich anderes Produkt
  - Skincare-Produkt aber Review redet von Kapseln/Tabletten/oral
  - Supplement aber Review redet von Eincremen/Auftragen
  - Erkennungsmuster: "Kapsel", "Tablette", "geschluckt" bei topischem Produkt (und umgekehrt)
- **[MANUFACTURER]**: Produktbeschreibung statt echte Kundenstimme
  - Erkennungsmuster: "Das Set enthaelt...", "Die Produkte werden...", "Der Hauptwirkstoff...", "Hergestellt in...", "Ist konzipiert als..."

### Trusted Review Platforms
amazon.de, amazon.com, trustpilot.com, reddit.com, gutefrage.net, idealo.de, geizhals.de, testberichte.de, beautypedia.com, inci.de, gesundheitsfrage.net

## Study Tier System

| Tier | Beschreibung | Gewicht | Tag |
|------|-------------|---------|-----|
| TIER 1 | RCTs in Top-Journals (Lancet, NEJM, JAMA, BMJ, Cochrane) | Hoechstes | — |
| TIER 2 | Prospektive Studien, Meta-Analysen | Hoch | — |
| TIER 3 | Observationsstudien, Kohortenstudien, Cross-Sectional | Mittel | — |
| TIER 4 | In-vitro, Tierstudien | Niedrig | [EXTRAPOLATION] |
| TIER 5 | Expertenmeinung, Herstellerstudien, Fallberichte | Minimal | [WEAK SOURCE] |

Regel: Im Briefing Section 7 bevorzugt TIER 1-2 zitieren. TIER 4-5 nur als Zusatz.

## PMID-Verbot

NIEMALS PMIDs (PubMed IDs) angeben — nur DOI-Nummern (Format: `10.xxxx/xxxxx`).
PMIDs werden NICHT validiert und koennen halluziniert sein.
Studien ohne validierten DOI: nur Autor + Jahr + Journal zitieren, OHNE Identifikator.
