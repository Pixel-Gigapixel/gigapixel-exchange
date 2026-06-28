# Dims-Reconciliation (READ-ONLY, VERIFIZIERT) — falsche Maße in ai_description_de

## #2 — format_px ist autoritativ (gegen die ECHTE Datei bewiesen)
`format_px`/`format_width`/`format_height` werden vom `DatamapDataHandlerHook::getImageProperties()` aus der
Zoomify-`ImageProperties.xml` der echten Bild-Pyramide gelesen (WIDTH/HEIGHT). Unabhängiger Gegencheck —
ich habe die live `ImageProperties.xml` direkt gecurlt (`https://www.large-format.photography/gigapixelKacheln/<bild>/`):

| uid | Bild | ECHT (Zoomify-XML) | format_px | ai_de = **ES** |
|---|---|---|---|---|
| 3 | Burji-Khalifa | **10783×23225** | 10783×23225 ✓ | 34055×73345 ✗ |
| 4 | Ahorn | **26412×9467** | 26412×9467 ✓ | 60896×21826 ✗ |
| 5 | Ameisenstrasse | **37394×6694** | 37394×6694 ✓ | 77709×13911 ✗ |
| 7 | Ameisenstrasse2 | **26396×9483** | 26396×9483 ✓ | 47164×16944 ✗ |
| 272 | Ilmenau-Fruehling | **34297×7299** | 34297×7299 ✓ | 104496×22239 ✗ |

**5/5: format_px == echte Datei. ai_de/ES ist falsch** (~3,16× linear = √10 → 10× GP). FR/RU == echt = korrekt.

## #1 — Ursache: LLM-Halluzination in FillDescriptions (kein Spalten-/Rechenfehler)
`FillDescriptionsCommand` übergibt dem LLM `format_px` + `format_w/h` und sagt „pixel dimensions **from format_px**".
Die Quelle war also **korrekt**; das LLM hat bei der Generierung für diese Records die Maße **frei erfunden**
(konsistent ~√10 zu groß, GP passt zur falschen Dim → intern stimmig, faktisch falsch).
**Konsequenz:** Ein FillDescriptions-**Re-Run würde den Fehler reproduzieren können** (nondeterministisch).
→ **Deterministischer Patch aus `format_width/height` (kein LLM)** ist der sichere Weg.

## #3 — Exakte betroffene Menge (punkt-/space-tausender-bewusst geparst)
| Klasse | n |
|---|---|
| **dims_wrong** (Maß ≠ format_w×h) | **1.554** |
| **gp_wrong** (Maß ok, aber GP-Figur ≠ truth, z. B. uid 7265 „14" statt „0,14") | **9** |
| **=> BETROFFEN (Patch-Ziel)** | **1.563** |
| no_dim (HIST/GRAFIK ohne Maßangabe — separate Mini-Lücke, nicht „falsch") | 137 |
| no_gp (HIST/GRAFIK ohne GP-Figur — legitim) | 2.146 |
| both_ok (Maß+GP korrekt) | 7.189 |

uid-Liste der 1.563: `dims_affected_uids.json`. (Frühere „1.704/19%" war vor dem Tausenderpunkt-Fix überzählt.)

## Tragweite
- **DE-Live-Seite** zeigt die falschen Maße ebenfalls (rendert `ai_description_de` direkt) — 1.563 Produkte.
- **ES**: dieselben falschen Maße (geerbt). **FR/RU**: korrekt (Pre-Korruptions-Übersetzung).

## Vorschlag (dein Call — kein Write erfolgt)
**Root-Fix (behebt DE + ES, deterministisch, kein LLM):**
1. `ai_description_de` der **1.563** patchen: das `W × H`-Maß **und** die `X,XX GP/Gigapixel`-Figur aus
   `format_width/height` neu setzen (GP = W·H/1e9, Komma-Dezimal; Format/Tausenderstil des Records erhalten).
   Transaktional, Backup, Vorab-SELECT des Match-Sets (wie beim `por ía`-Fix). → behebt die **DE-Seite**.
2. `gigapixels:translate --language=es --fields=description` → MD5 greift **automatisch nur die 1.563**
   (geänderter source_hash) → ES neu aus korrigierter Quelle. (Re-Gate danach: dims byte-genau.)
3. **FR/RU** unangetastet (bereits korrekt).
4. Optional separat: die **137 no_dim** (HIST/GRAFIK ohne Maß) — eigene Entscheidung, ob Maß ergänzt wird.

> Read-only. Kein DE-Source-Write / kein Re-Translate bis zu deinem GO.
