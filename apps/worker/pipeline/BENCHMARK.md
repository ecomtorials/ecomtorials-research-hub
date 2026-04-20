# Ecomtorials Research Pipeline - Benchmark Tests

 Schneller und günstiger Benchmark-Test für Research-Qualität (Pipeline vs App).

## Übersicht

**Ziel:** Einen schnellen und günstigen Benchmark-Test erstellen, um die Research-Qualität zwischen:
- **Standalone Pipeline** (`research-pipeline/`)
- **Web App** (`ecomtorials-app/`)

zu vergleichen.

**Anforderung:** Schnell (<5min) und günstig (keine API-Calls nötig, nur Unit-Tests).

## Teststruktur

### 1. Quality-Benchmark Tests (`app/tests/test_quality_benchmark.py`)

Testet die Quality-Review-Logik mit Mock-Daten.

**Tests:**
| Test | Zweck | Dauer |
|------|-------|-------|
| `test_quality_review_perfect_scores` | Prüft Qualitätsscores bei guten Inputs | ~30ms |
| `test_quality_review_missing_criteria` | Prüft Punktabzug bei fehlenden Kriterien | ~30ms |
| `test_quality_review_threshold` | Prüft Threshold-Logik (7.0 default) | ~30ms |
| `test_quality_review_metrics` | Prüft alle erwarteten Metriken | ~30ms |

**Kosten:** $0 (keine API-Calls)
**Dauer:** ~0.12 Sekunden

### 2. Pipeline-Benchmark Tests (`app/tests/test_pipeline_benchmark.py`)

Testet Basiskonfiguration und Struktur ohne API-Aufrufe.

**Tests:**
| Test | Zweck | Dauer |
|------|-------|-------|
| `test_research_config_defaults` | Prüft Turn-Budgets und Threshold | ~30ms |
| `test_research_config_budgets` | Prüft Budget-Struktur | ~30ms |
| `test_doi_regex_pattern` | Prüft DOI Regex-Pattern | ~30ms |
| `test_url_regex_pattern` | Prüft URL Regex-Pattern | ~30ms |
| `test_quality_review_threshold` | Prüft Threshold mit Empty Content | ~30ms |
| `test_quality_review_basic` | Prüft grundlegende QR-Funktionalität | ~30ms |
| `test_quality_review_metrics` | Prüft Metrik-Struktur | ~30ms |

**Kosten:** $0
**Dauer:** ~0.12 Sekunden

## Quality Review Logic

### Scoring-System

Beide Implementierungen (Pipeline & App) verwenden die gleiche Logik:

#### R1/R2 Scoring (Basis: 10.0, Abzüge pro fehlendem Element)

| Kriterium | Mindestwert | Abzug |
|-----------|-------------|-------|
| R1 Kategorien | 20 von 25 | 0.3 pro fehlende Kategorie |
| R2 VoC Kategorien | 8 | 0.3 pro fehlende Kategorie |
| Quotes | 15 | 0.1 pro fehlendes Zitat |
| URLs | 30 | 0.05 pro fehlende URL |
| Produktspezifität | Brand 10x erwähnt | -2.0 |

#### R3 Scoring (Basis: 10.0, Abzüge pro fehlendem Element)

| Kriterium | Mindestwert | Abzug |
|-----------|-------------|-------|
| DOIs | 5 | 0.8 pro fehlender DOI |
| UMP | Vorhanden | -2.0 |
| UMS | Vorhanden | -2.0 |
| Killer-Hooks | Vorhanden | -1.0 |

### Threshold

**Bestanden:** `overall >= 7.0`

## Gemeinsame quality.py Module

Um Konsistenz zu gewährleisten, wurde `research-pipeline/quality.py` erstellt, das von beiden Implementierungen verwendet werden kann.

### Funktionssignatur

```python
def quality_review(
    r1a: str,
    r1b: str,
    r2_final: str,
    r3_final: str,
    brand: str = "TestBrand",
    threshold: float = 7.0,
) -> dict:
```

### Return-Struktur

```python
{
    "qr_r1r2": {"score": float, "issues": list[str]},
    "qr_r3": {"score": float, "issues": list[str]},
    "overall": float,
    "summary": str,
    "metrics": dict,
}
```

### Metriken

| Key | Beschreibung |
|-----|--------------|
| `r1_categories` | Anzahl gefundener R1-Kategorien |
| `url_count` | Anzahl gefundener URLs |
| `r2_voc_categories` | Anzahl erkannter VoC-Kategorien |
| `quote_count` | Anzahl Kundenzitate |
| `doi_count` | Anzahl gefundener DOIs |
| `has_ump` | UMP ist vorhanden |
| `has_ums` | UMS ist vorhanden |
| `has_hooks` | Killer-Hooks sind vorhanden |
| `brand_mentions` | Brand-Namen-mentioned |
| `is_product_specific` | Produkt ist spezifisch |

## Verwendung

### Unit-Tests für Quality (Sekunden)

```bash
python3 -m pytest app/tests/test_quality_benchmark.py -v
```

### Alle Tests zusammen

```bash
python3 -m pytest app/tests/ -v
```

### Erwartungsergebnis

- **59 tests** insgesamt
- **59 passed** bei erfolgreicher Implementierung
- **Dauer:** ~0.3 Sekunden

## Kostenprognose

- **Unit-Tests:** $0 (keine API-Calls)
- **E2E-Test (klein):** ~$0.05-0.10 (wenig Turns)
- **Dauer:** <5 Minuten total

## Wartung

### Test-Content aktualisieren

Die Test-Content-Blöcke (`R1A_CONTENT`, `R1B_CONTENT`, `R2_CONTENT`, `R3_CONTENT`) müssen bei Änderungen an der Quality-Review-Logik überprüft werden.

### Neue Tests hinzufügen

1. Füge Test-Funktion mit `test_`-Prefix hinzu
2. Verwende `assert` für Erwartungen
3. Keine externen Abhängigkeiten (keine API-Calls)
4. Kurze Laufzeit (<100ms pro Test)
