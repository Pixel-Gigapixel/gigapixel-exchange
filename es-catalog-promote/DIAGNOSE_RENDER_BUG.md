# Diagnose: ES-Produktübersetzungen rendern nicht (READ-ONLY, kein Fix)

Served-Check auf gmbh: `/es/`-Produktseiten zeigen Titel/Beschreibung weiter DE/EN, obwohl die 26.472
ES-Rows in `tx_gigapixels_translation` liegen. **Root-Cause = Rendering-Layer, nicht DB.**

## #1 — DB ist korrekt (gmbh)
```
language='en' 14813 · 'es' 26472 · 'fr' 26419 · 'ru' 26455
```
`'es'` exakt (nicht `es_ES`), Count == promotet (26.472). Die Promotion war sauber; die Rows sind da.

## #2 — ROOT CAUSE: vier hardkodierte `langId→code`-Maps, alle ohne `4 => 'es'`
ES (langId 4) wurde als Site-Sprache + DB-Rows ergänzt, aber die Sprachcode-Ableitung im Theme nie auf 4
erweitert. Jeder Konsument von `tx_gigapixels_translation` bricht für ES auf seinen Default:

| Datei | Map / Bedingung | ES (4) → | Wirkung |
|---|---|---|---|
| `dg_theme/.../Plugins/Gigapixel/Show.html` Z.150–153 (description) | `{currentLanguageId} == 2 \|\| == 3`; langCode 2→fr/else→ru | **Bedingung false** | Description-Block übersprungen → DE-Fallback (`aiDescriptionDe`) |
| `cart_gigapixels/.../DisplayTitleViewHelper.php` (H1, Teaser, Liste, Suche) | `match: 1=en,2=fr,3=ru,default=en` | **default `en`** | Titel englisch/DE statt ES — H1 via `cartgigapixels:displayTitle` |
| `cart_gigapixels/.../OgTagsViewHelper.php` | `1=en,2=fr,3=ru,default=de` | **`de`** | og:title/description deutsch |
| `cart_gigapixels/.../SchemaViewHelper.php` | `1=en,2=fr,default=en` (sogar ohne ru!) | **`en`** | Schema.org-Daten englisch |

→ Asymmetrie fr(rendert) vs es(nicht) ist exakt hier: 2/3 sind in den Maps, 4 nicht.

**Fix (NICHT jetzt — auf Daniels GO):** `4 => 'es'` in den 3 ViewHelper-`match()` + Show.html-Condition
(`== 2 || == 3 || == 4`) und langCode (`== 4 → es`) ergänzen. Reiner **Code-Change + Deploy** (biz+gmbh);
die 26.472 DB-Rows bleiben unangetastet (kein Rollback). `SchemaViewHelper` braucht zusätzlich `3 => 'ru'`
(RU fehlt dort auch — separater Alt-Bug).

## #3 — Dims (SEKUNDÄR, separat, betrifft FR/RU gleichermaßen)
`ai_description_de` trägt die Maße, die B/C byte-genau übersetzen. Stichprobe 400 Records: **~8% (33)**
mit `ai_description_de`-Maß ≠ `format_px` (z. B. uid 4: desc `60896×21826`=1,33 GP vs `format_px`
`26412×9467`=0,25 GP). Das sind unterschiedliche Metriken (Voll-Auflösung vs. ZOOM/Datei-px).
**Offene Frage:** welche ist autoritativ? Falls `format_px`/Datei-Metadaten die Wahrheit ist, tragen ~8% der
ai_description_de (und damit FR/RU/ES-Beschreibungen) falsche Maße — ein **DE-Quelldaten-Thema**
(`FillDescriptionsCommand`), unabhängig vom Render-Bug und nicht ES-spezifisch. Kein Teil dieser Promotion.

## Fazit
- Promotion korrekt, **keine Rollback** nötig. Es ist ein Lookup/Map-Bug im Theme-Code.
- Blocker für „A+B+C live auf gmbh": die 4 Map-Stellen. Sobald `4 => 'es'` ergänzt + deployed ist, rendern
  Titel (H1/Liste/Suche), Beschreibung, og/Schema spanisch — ohne DB-Änderung.
- #3 (Dims) ist ein separater, sprachübergreifender Daten-Befund für eine eigene Entscheidung.
