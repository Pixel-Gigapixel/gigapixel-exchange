# Glossar-Term-Dry-Run (55 Terme) — Review · KEIN Insert

## Lauf
Übersetzer reused translate_fields + TRANSLATION_GUIDE.md (Sonnet; keiner über „lang"-Schwelle).
Pro Term übersetzt: title · short_definition · long_definition · meta_description · FAQ-Q/A.
slug = slugify(ES-Titel) · faq_items JSON-strukturerhaltend · canonical_url leer (DE leer).
gates-artige Prüfung je Prosa-Feld: Zahlen-Multiset == DE · kein „KI"-Residue (→ IA) · keine DE-Prosa-Reste.

## Ergebnis
- 55/55 übersetzt · **0 geflaggt** (alle Checks grün) · **0 Slug-Kollisionen** (unter den 55)
- term-NNN.json je Term: ES-Felder + `_de` (DE-Quelle) + `_checks` + `_model`
- slugs.txt: 55 × (DE-slug → ES-slug) + Kollisionscheck

## Für deinen Review
- ALLE 55 Slugs (SEO) in slugs.txt
- Stichprobe Definitionen (short/long/meta) + FAQ je Term
- ⚠️ Terminologie: Schreibweise „gigapíxel" (Gattungswort, klein/akzent) vs. Marke „Gigapixel" variiert
  zwischen Termen — bitte festlegen, welche Form wo gilt (Markenname vs. Begriff).
- Kategorie-Relation/related_terms/example_images/Workflow-Meta werden beim Load aus DE KOPIERT (nicht übersetzt).

## Nach deinem GO (separater Load-Schritt)
55 Term-Rows (lang4, l10n_parent=DE-uid, pid=391) + 7 Kategorie-Overlays (deine 7 ES) +
je 1 ES-Plugin-list-Element auf 391/392.
