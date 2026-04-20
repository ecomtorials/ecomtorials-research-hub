# Ingredient Quality Filters (Shared)

## BANNED (Marketing-Labels — NICHT Wirkstoffe → VERWERFEN)

```
natürlich, naturrein, premium, hochdosiert, laborgeprüft,
bio-zertifiziert, vegan, glutenfrei, ohne Zusätze, rein pflanzlich,
dermatologisch getestet, klinisch erprobt, hochwirksam, einzigartig,
revolutionär, innovativ, traditionell, altbewährt, hauteigen,
evidenzbasiert, wohltuend, revitalisierend, regenerierend, synergie,
ganzheitlich, kraftvoll, intensiv, pflegend
```

## TOO_GENERIC (Oberbegriffe — müssen ANGEREICHERT werden)

Reale Substanzklassen, aber zu unspezifisch für UMP/UMS-Research.

```
Lipide, Fettsäuren, Vitamine, Mineralstoffe, Aminosäuren,
Antioxidantien, Enzyme, Probiotika, Präbiotika, Kollagen, Peptide,
Extrakt (ohne Pflanzenname), Öle (ohne spezifisches Öl),
Nährstoffe, Spurenelemente, Proteine
```

## Enrichment-Logik

1. **BANNED-Check**: Jeder extrahierte Wirkstoff → gegen BANNED prüfen → Match = VERWERFEN
2. **TOO_GENERIC-Check**: Gegen TOO_GENERIC prüfen → Match = ANREICHERN:
   - Zusätzliche WebSearch: `"[Produktname] [generischer Begriff] spezifische Form INCI"`
   - Ersetze generisch durch spezifisch (z.B. "Fettsäuren" → "Ölsäure (Oleic Acid)")
3. **Fallback**: Keine spezifische Form gefunden → behalten mit `[GENERIC — specify in R3]`
4. **Set/Bundle-Produkte**: Wenn 10+ Inhaltsstoffe → Enrichment nur für Top 5 mit höchster Angle-Relevanz

## Sibling-Product Detection (v12.17)

Identifiziere andere Produkte DESSELBEN Herstellers → verhindert Cross-Contamination in Reviews.

### Ablauf

1. **Erkennung**: Beim Produkt-Scraping (Step 1) alle sichtbaren Produktnamen des gleichen Herstellers sammeln
2. **Liste anlegen**: `siblingProducts[]` — z.B. `["Nachtcreme", "Serum", "Reinigungsgel"]` wenn wir die "Tagescreme" recherchieren
3. **Filter anwenden**: Reviews die Sibling-Keywords enthalten → `[WRONG-PRODUCT: Sibling]` markieren und LÖSCHEN

### Category Conflict Keywords

Automatisch aufbauen basierend auf Produkt-Kontext:

- **Wenn Produkt = Creme/Serum/Topisch**: Blockiere `"trinken"`, `"schlucken"`, `"Tablette"`, `"Pulver"`, `"Kapseln"`, `"Dosierung"`, `"Magenbeschwerden"`
- **Wenn Produkt = Supplement/Kapsel/Pulver**: Blockiere `"auftragen"`, `"einmassieren"`, `"Hautgefühl"`, `"Textur"`, `"eincremen"`, `"Konsistenz"`
- **Wenn Produkt = Textil/Bettwäsche**: Blockiere `"schlucken"`, `"Nebenwirkungen"`, `"Dosierung"`, `"auftragen"`

### Beispiel

```
Produkt: "Tallow Naturals Wohlfühlset" (Creme)
siblingProducts: ["Tallow Serum", "Tallow Lippenpflege", "Tallow Bartöl"]
Blocked Keywords (Nische): ["trinken", "schlucken", "Tablette", "Pulver", "Kapseln"]

Review: "Ich nehme die Tallow Kapseln seit 3 Wochen..." → [WRONG-PRODUCT: Sibling] → LÖSCHEN
Review: "Die Tagescreme zieht schnell ein..." → OK (passt zur Nische)
```
