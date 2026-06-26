# ES-i18n + Glossar — Inputs für Daniel

## (A) Visual-Search-XLIFF (38 Strings) — zur Übersetzung
- `locallang.xlf`     = DE-Quelle, 38 `<source>` (Suchfeld, Drop-Zone, Slider, Badges, Treffer, Sortierung, Tooltips)
- `fr.locallang.xlf`  = FR-Vorbild, 38 `<target>` (Terminologie/Struktur)
→ Du verfasst die 38 ES-`<target>`; ich baue daraus `es.locallang.xlf` (Mirror von fr/ru, gleiches id-Set).
Befund: EN/FR/RU je 38 Targets, **ES 0** → ganze Visual-Search-UI auf /es/ aktuell deutsch (Source-Fallback).
Datei lebt in `packages/gigapixels_visualsearch/Resources/Private/Language/`.

## (B) Glossar-Struktur — für den ES-Daten-Mirror-Plan

### Speicherung
- ALLE Glossar-Records auf **pid=391**. Terme: lang0/1/2/3 je **55**; **lang4 (ES) = 0**.
- Kein separates Methodik-Table: die Methodik-Seite (392) rendert dieselben Terme, gefiltert über
  Flag `is_methodology_term=1`.

### Lokalisierungskette (connected mode, NUR l10n_parent — KEIN l10n_source)
DE = lang0 (l10n_parent=0). Übersetzung: neue Row mit sys_language_uid=N, **l10n_parent = DE-uid**, pid=391.
```
term uid 1  lang0  l10n_parent 0   'Gigapixel-Aufnahme'   slug gigapixel-aufnahme
  ├ uid 30  lang1  l10n_parent 1   'Gigapixel Image'      slug gigapixel-image
  ├ uid 111 lang2  l10n_parent 1   'Prise de vue gigapixel' slug prise-de-vue-gigapixel
  └ uid 166 lang3  l10n_parent 1   'Гигапиксельная съёмка'  slug gigapiksel-naia-syomka
term uid 2  lang0  'Stitching' → EN 'Stitching', FR 'Assemblage (Stitching)', RU 'Склейка (Stitching)'
```
→ ES-Mirror: 55 Rows lang4, l10n_parent=DE-uid, pid=391. slug WIRD übersetzt (wie FR/RU).

### Übersetzbare Felder (term)
title · slug · short_definition(400) · long_definition(mediumtext) · meta_description(320) ·
faq_items(mediumtext, FAQ-JSON) · canonical_url(ES neu generieren)
KOPIEREN (nicht übersetzen): category(Relation→cat-uid) · related_terms · example_images · status ·
source_*/generator_model/reviewer_* (Workflow-Meta) · quality_score · is_methodology_term · robots · image_query

### Kategorien (7) — ACHTUNG Abweichung
`_category` hat **nur lang0** (uids 1–7: Aufnahme/Verarbeitung/Produktion/Druck/Medien/Technik/Anwendung).
**FR/RU haben die Kategorien NICHT lokalisiert** (0 Overlays). Dein Plan nennt „7 Kategorien auf langId 4" —
das wäre ES *über* FR/RU-Parität hinaus. ENTSCHEIDUNG: ES-Kategorien lokalisieren (geht über FR/RU) oder
DE-Kategorien spiegeln (Parität)?

### Seed-TSV  scripts/glossar-seed/glossar_de_en_export_20260618.tsv
56 Zeilen (1 Header + 55). Spalten:
`uid | slug | title_de | title_en | short_de | short_en | long_de | long_en | faq_de | faq_en | meta_de | meta_en | image_query`
→ DE↔EN-Export, mappt 1:1 auf die term-Felder; war die EN-Seed-Quelle.
ES-Analog: TSV mit *_es-Spalten (title_es/short_es/long_es/faq_es/meta_es), keyed auf uid/slug →
Loader inserted lang4-Rows mit l10n_parent=DE-uid.

### ES-Plugin-Element (391/392)
Zusätzlich je 1 tt_content `list`-Element (sys_language_uid=4) auf 391 (glossary) und 392 (methodology),
damit das Plugin im ES-Kontext rendert. 392 filtert über is_methodology_term.
