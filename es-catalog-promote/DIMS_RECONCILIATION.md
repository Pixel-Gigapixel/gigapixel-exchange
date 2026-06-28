# Dims-Reconciliation (READ-ONLY) — falsche Maße in ai_description_de

## Befund (über alle 8.889)
- **1.704 Records (19%)**: `ai_description_de`-Maß ≠ `format_width × format_height` (= echte Datei-Dim, == `format_px`).
- Beleg (uid: ai_de/ES | FR | echt):
  | uid | ai_de = **ES** | **FR** | echt (format_px) |
  |---|---|---|---|
  | 3 | 34055×73345 | 10783×23225 | **10783×23225** |
  | 4 | 60896×21826 | 26412×9467 | **26412×9467** |
  | 5 | 77709×13911 | 37394×6694 | **37394×6694** |
  | 272 | 104496×22239 | 34297×7299 | **34297×7299** |
- Empirie (200er-Mismatch-Sample): **FR-desc-Dim == format_px in 92,5%**, FR == ai_de nur 3/200.

## Was wirklich passiert ist
1. `FillDescriptions` soll die Maße „from format_px" nehmen (`format_px == format_width×height` = echte Datei).
2. `ai_description_de` wurde irgendwann **neu generiert** und produzierte für 1.704 Records **falsche** Maße
   (z. B. ~10× zu groß; intern konsistent — die „X,XX GP" passt zur falschen Dim, ist aber faktisch falsch).
3. **FR/RU** wurden **vor** dieser Neugenerierung übersetzt → tragen die **korrekten** format_px-Maße.
   (Das sind exakt die ~1.632 Records mit `source_hash ≠ MD5(aktuelle ai_description_de)` von der C-Prep.)
4. **ES** wurde **nach** der Korruption aus der aktuellen ai_description_de übersetzt → erbte die **falschen** Maße.

## Tragweite — nicht nur ES
- **DE-Live-Seite** zeigt die falschen Maße ebenfalls (rendert `ai_description_de` direkt). 19% der DE-Produkte.
- **ES**: dieselben falschen Maße (geerbt).
- **FR/RU**: korrekt (Zufall der Übersetzungs-Reihenfolge).
- **format_px / format_width×height = autoritativ** (echte Datei-Metadaten).

uid-Liste der 1.704: `dims_wrong_uids.json` (im selben Ordner).

## Vorschlag (dein Call — kein Write erfolgt)
**Empfohlen (Root-Fix, behebt DE + ES gemeinsam):**
1. `ai_description_de` für die 1.704 korrigieren — die Maße `W × H` und die abgeleitete `X,XX GP/Gigapixel`
   deterministisch aus `format_width/height` neu setzen (GP = W·H/1e9, Komma-Dezimal). Entweder
   chirurgischer prosa-Replace (Dim + GP) oder gezielter `FillDescriptions`-Re-Run **nur** auf die 1.704.
   → behebt die **DE-Live-Seite**.
2. Danach `gigapixels:translate --language=es --fields=description` greift via MD5 **automatisch nur die 1.704**
   (geänderter source_hash) → ES wird aus der korrigierten Quelle neu übersetzt.
3. **FR/RU nicht anfassen** (bereits korrekt) — außer du willst Konsistenz erzwingen (dann auch deren
   1.704 re-translaten, aber unnötig).

**Alternative (nur ES, schneller, lässt DE falsch):** die Maße+GP direkt in den 1.704 ES-description-Rows
chirurgisch ersetzen (wie der `por ía`-Fix). Nicht empfohlen — DE bliebe falsch sichtbar.

**Offen vorab zu klären:** WARUM hat die ai_description_de-Neugenerierung falsche Maße erzeugt (FillDescriptions-
Bug? falsche format_px-Quelle zum Generierungszeitpunkt?) — sonst reproduziert ein Re-Run den Fehler.
Empfehlung: erst die 1.704 deterministisch aus format_width/height patchen (kein LLM), dann ES re-translaten.

> Read-only. Kein Fix-Write bis zu deiner Entscheidung.
