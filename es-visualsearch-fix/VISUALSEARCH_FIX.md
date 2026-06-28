# Visual-Search-Karten „Imágenes similares" rendern EN/DE — Fix (langId 4→es)

## Mein Fehler im ersten Trace
Ich hatte nur den `relatedGigapixels`-Carousel (`RelatedGigapixel.html`, nur `alt`=displayTitle) geprüft —
NICHT die Visual-Search-KARTEN (Scores 1.00/0.95 = `gigapixels_visualsearch`), die Titel+Beschreibung+Kategorie rendern.
Das ist der gemeldete Bug.

## Beleg am ECHTEN gerenderten Output (gmbh /es/details/burji-khalifa-in-dubai, VOR Fix)
Karten-Beschreibungen = **Englisch**: „Genuine camera capture", „no AI generation", „no AI upscaling",
„Ultra-high-resolution"; Kategorie „cityscape"/„architecture" EN. (siehe `beleg_EN_cards_before.txt`)

## Root-Cause: 2 Service-Stellen, `match()` ohne `4=>'es'`
- **`EmbeddingSearchService::enrichLocalizedData`** (Z. 84): Basis-`description` für Nicht-DE = `ai_description_en`;
  `enrichLocalizedData` ersetzt für fr/ru description→`data['description']` + title→`data['primary_subject']`.
  ES(4) fiel auf `default=>null` → `return` → **keine Lokalisierung** → Beschreibung bleibt EN, Titel DE.
- **`KeSearchAdapter::searchByText`** (Z. 32): dieselbe `match{2,3,default}` → Textsuche-Ergebnisse ES = EN.
- `3=>'ru'` ist in beiden vorhanden (kein ru-Altbug).

## Patch (`visualsearch-fix.diff`) — je 1 Zeile `4=>'es'`
- `EmbeddingSearchService.php`: working-tree == HEAD + `4=>'es'` (clean, nur diese Zeile).
- `KeSearchAdapter.php`: trägt im Working-Tree **vorbestehende** Photographer-Feature-Änderungen
  (`use PhotographerName` + `detectPhotographer()`), die auf die **nicht-deployte** `PhotographerName.php` zählen.
  → **isolierte** Datei `KeSearchAdapter.isolated.php` = HEAD + NUR `4=>'es'` (0 Photographer-Reste, verifiziert).

## (c) Kategorie-Badge `scene_type` — SEPARAT, kein 4=>es
`{result.data.scene_type}` = `ai_scene_type` (englische Scene-Labels „cityscape"/„architecture") — eigenes Feld,
NICHT von enrich übersetzt. Braucht ein **scene→es-Mapping** (eigene Mini-Entscheidung), nicht Teil dieses Fixes.
Nach dem Fix sind Karten-Titel + -Beschreibung spanisch (inkl. der korrigierten Maße, da die es-Beschreibungen die
gepatchten Dims tragen); nur das Kategorie-Badge bliebe EN.

## Deploy-Plan (auf dein Diff-Grün)
1. **EmbeddingSearchService.php** (working-tree, clean) → behebt den gemeldeten Karten-Bug.
2. **KeSearchAdapter** = `KeSearchAdapter.isolated.php` deployen ALS KeSearchAdapter.php (Photographer-Hunk draußen)
   → behebt Textsuche-ES. (Oder: KeSearchAdapter aufschieben bis das Photographer-Feature + PhotographerName.php
   gemeinsam deployt werden — dein Call; EmbeddingSearchService reicht für den gemeldeten Bug.)
3. biz → served-Recheck → gmbh → dein web_fetch-Recheck (Karten-Beschreibung „…sin upscaling por IA", Titel spanisch, Maße korrekt).
