# es-it-pilot — IT (langId 7) Enablement, Review-Bundle (KEIN Deploy)

Vor-Deploy-Review für den IT-Pilot. Nichts hiervon ist auf biz/gmbh geschrieben.
Reihenfolge nach Daniels Freigabe: **biz zuerst → gerendertes /it/-HTML zeigen → erst dann gmbh (eigener GO)**.

## 8-Datei-Deploy-Set

| # | Datei | Diff-Typ | Entanglement |
|---|-------|----------|--------------|
| 1 | config/sites/main/config.yaml | working-tree | sauber |
| 2 | …/Setup/Lib/LanguageMenu.typoscript | working-tree | sauber |
| 3 | cart_gigapixels/…/DisplayTitleViewHelper.php | working-tree | sauber |
| 4 | cart_gigapixels/…/OgTagsViewHelper.php | working-tree | sauber |
| 5 | cart_gigapixels/…/SchemaViewHelper.php | working-tree | sauber |
| 6 | gigapixels_visualsearch/…/EmbeddingSearchService.php | working-tree | sauber |
| 7 | gigapixels_visualsearch/…/KeSearchAdapter.php | **ISOLIERT** | Photographer-Feature im Working-Tree |
| 8 | dg_theme/…/Plugins/Gigapixel/Show.html | **ISOLIERT** | Photographer-Feature im Working-Tree |

`diffs/` = die 8 Diffs. `isolated/` = die 2 isolierten **vollen Deploy-Artefakte** (#7, #8).

## Inhaltliche Änderung (alle 8 Dateien)
Ausschließlich die langId→Code-Verdrahtung **5=>'tr', 6=>'pl', 7=>'it'** (zusätzlich zu bestehendem `4=>'es'`),
plus config.yaml langId-7-Block (Route /it/, fallback→DE) + LanguageMenu (`…,7` / `|| IT` / `|| &L=7`).
Show.html: `condition == …||5||6||7` + `<f:case>5→tr/6→pl/7→it`.

## Entanglement (B) — die Crash-Falle
`KeSearchAdapter.php` und `Show.html` tragen im Working-Tree das **uncommittete Photographer-Mode-Feature**
(`detectPhotographer`/`searchByPhotographer`, `<vs:photographerLink>`, `xmlns:vs`) — hängt an der **untracked**
`PhotographerName.php`. Wholesale-Deploy → gmbh fatal'et an fehlender Klasse.
→ Deploy-Artefakte #7/#8 sind **HEAD + nur der langId-Hunk**. Beweis: `CRASH_CHECK.txt` (0× Residue) +
`diffs/07…`, `diffs/08…` zeigen ausschließlich die langId-Zeilen.

Review-Greps:
    grep -E "PhotographerName|xmlns:vs|vs:|detectPhotographer|searchByPhotographer" isolated/*   # = 0
    cat diffs/07_KeSearchAdapter.ISOLATED.diff diffs/08_Show.html.ISOLATED.diff                  # = nur 5/6/7

## Befund A — Render-Spots waren NICHT für 5/6/7 verdrahtet
HEAD (committed) hatte in allen 7 Spots nur bis `4=>'es'`. Die 5/6/7-Zeilen existierten **nie** im Repo —
die Nacht-Summary („pre-wire deployed") war überstellt; **kein Regress**.

**/es/-Live-Gegenprobe auf gmbh (jetzt):**
GET https://gigapixel.gmbh/es/details/schloss-belvedere-bei-weimar → HTTP 200,
`<html lang="es-ES">`, 15 Spanisch-Marker (`como toma de`, `gigapíxeles`, `píxeles`), **0 DE-Residue**.
→ `4=>'es'` ist live & stabil; nur 5/6/7 fehlte. ES/FR/RU unbedroht.

## Step 1 (separat, schon validiert)
`promote_es_catalog.py` → `--lang` generalisiert. IT-Dry-Run: biz IT 8.760/8.823/8.889 ✓, Idempotenz ok (gmbh IT=0).
Nicht Teil dieses 8-Sets; läuft als Step 3 (gmbh) nach biz-Grün.
