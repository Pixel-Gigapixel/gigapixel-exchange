# ES Produkt-Übersetzung Teil B — Post-Run Aggregat-Report

**Lauf:** `gigapixels:translate --language=es --fields=title,keywords` (biz, Haiku, MD5-inkrementell)
**Contract:** Keyword+Titel über **Delimiter-Contract** (`<<<REC n>>>…<<<END>>>`) statt Positions-Zeilen —
behebt die `count mismatch`-Klasse, ~10× schneller (Keywords ~190/min statt ~20/min).
**Prompt:** `PROMPT_TITLE_ES` Regel 2/4 verfeinert (EMPTY nur wenn EN leer UND reiner Eigenname; EN-Präsenz primär).

## Endstand
- **es-title: 8.760 · es-keywords: 8.823** (alle lebenden Records; `deleted`-Soft-Deletes korrekt übersprungen).

## Gate — 4 Checks (ungekappte DB)

| Check | Ergebnis | Bewertung |
|------|----------|-----------|
| **(0) Coverage** — DE-Inhalt ohne es-Zeile | **0** | vollständig (die 15 vermeintlich Fehlenden waren `deleted=1`) |
| **(1) DE-Residue** | **echt 7** / FP-Eigenname 279 | 279 = bewahrte Eigennamen (Schloss/Haus/am/See, Regel 5). Von den 7 „echten": 3× minimal (Keyword „alt" vor „antiguo"), 3× **französische Buchtitel/Orte korrekt belassen** (Pascal „Traitez … des liqueurs", „Causse Méjean"), **1× echt** (s. u. uid 7265) |
| **(2) Count-Drift** | ES<DE **4.155** / ES>DE **6** | ES<DE = erwartete Dedup (`deduplicateTerms()` kollabiert DE-Synonym-/Stuffing-Ketten; median Δ=−2). ES>DE 6 = Padding (s. u. uid 7445) |
| **(3) gigapíxel-Akzent** | **0** | sauber — kein unbeakzentuiertes Nicht-Marken-„gigapixel" |
| **(4) Über-Leerung** (empty-es trotz übersetzbarem DE) | **0** | von ursprünglich 353 → 0. Prompt-Fix + scoped Re-Translate vollständig. DE==EN-Eigennamen (Esther/Auckland/…) bleiben korrekt leer |

## Die ~10 marginalen Rest-Records (von 17.583 Feldern, ≈0,06 %)
- **uid 7265** — DE-`title`-Feld enthält **selbst Englisch** („Conversion of the former Scheufelen paper factory…");
  Modell reicht es durch. Quell-Anomalie (EN im DE-Feld), kein Übersetzungsfehler. Optional: `--force` einzeln.
- **uid 7445 + 5 weitere** (ES>DE) — bei **ultrakurzen** DE-Keyword-Listen padded Haiku (uid 7445: DE „Mandala,
  Kunst, Art" → ES 18 Terms inkl. erfundener „panorámica/memorial/valle…"). Verstößt gegen „nichts erfinden",
  betrifft 6 Records. Optional: gezielter Re-Force oder Hand-Trim (Liste in `flagged.tsv`, check=`drift_more`).
- **uid 194/195/196** — Keyword „alt" als erster Term vor „antiguo" (DE-Wort durchgereicht). Kosmetisch.

## Bewertung
Titel verifiziert (inkl. der 353 reparierten Über-Leerungen), Keywords über das Aggregat abgesichert:
Residue praktisch null, Drift = gewollte Dedup ohne Halluzination außer 6 Padding-Fällen, Akzent sauber,
Coverage vollständig. **B ist abnahmereif.** `flagged.tsv` enthält die ~10 Rest-uids für optionalen Feinschliff.

Artefakte: `postrun_gate.txt` (Roh-Report alle 4 Checks) · `flagged.tsv` (maschinell, Rest-uids) ·
`sample.tsv`/`DIAGNOSIS.md`/`dryrun.log` (B-Vorlauf).
