# Tier-1-Text Dry-Run (gehärtetes Tool 7abb68b) — Review

391/392 (Glosario/Metodología) RAUS → feature/glossary (plugin/datengetrieben, ES-Daten fehlen).

| pid | Modell | Gate | body | Status |
|----:|--------|------|-----:|--------|
| 142 | Opus   | PASS | 24.598z | ✅ sauber (Truncation-Beweis, vollständig) |
| 47 FAQ | Opus | PASS | 34.766z | ✅ sauber, KEINE Truncation (war der große Brocken); FAQ-Tag-Skelett via G1 byte-genau |
| 49 Datenschutz | Opus | PASS | 31.861z | ✅ sauber; DE-Header war leer → ES-Leerheader korrekt |
| 11 Impressum | Sonnet | PASS | 4.303z | ✅ sauber |
| 53 Ethik | Sonnet | PASS | 15.028z (4 Elem) | ✅ sauber |
| 45 Presse | Sonnet | **FAIL** | 40.030z (22 Elem) | 🔴 FALSCH-POSITIV: uid 111 = `<a>`-Link auf deutsche-handwerks-zeitung.de (URL bleibt verbatim, G3 flaggt sie). 21/22 sauber. --from-review würde blocken. |
| 46 Kontakt | Sonnet | PASS | 0z | ⚠️ PLUGIN: CType=form_formframework. Header ES, Body leer (Formular). Wie 391/392 — Labels aus Form-Definition, nicht tt_content. |

## Commit-bereit (5): 142, 47, 49, 11, 53
## Entscheidung nötig: 45 (Gate-Override für die URL?), 46 (Form-Lokalisierung separat?)
