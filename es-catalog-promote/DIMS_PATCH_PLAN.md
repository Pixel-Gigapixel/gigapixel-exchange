# Dims-Patch — Plan + Dry-Run (READ-ONLY, kein Write erfolgt)

## Exakte Menge (korrigiert)
- **1.558 Records** mit falschen Maßen in `ai_description_de` (dims_wrong) → Patch-Ziel.
- Die früher gemeldeten **9 „gp_wrong" waren False-Positives**: sie nutzen **Punkt-Dezimal-GP** („0.14 Gigapixel"),
  das der Gate als „14" fehlgelesen hatte. Tatsächlich = truth (0,14) → **korrekt, werden NICHT angefasst** (Beleg uid 7265 im Sample).
- 0 Skips (alle 1.558 validiert).

## Skript `patch_ai_de_dims.py` — Garantien
- **CHIRURGISCH:** `re.sub` ersetzt NUR den Maß-Span (`W × H [Pixel/px]`) und den GP-Span (`X,XX[-/ ]Gigapixel/GP`).
  Alles außerhalb bleibt **byte-exakt** (by construction). Skeleton-Check (Prosa ohne Zahl-Formatzeichen) bestätigt das.
- **Format-treu:** Separator `×`/`x`/`*`, Einheit `Pixel`/`px`, GP-Einheit `Gigapixel`/`GP`, Bindestrich-Form
  („1,87-Gigapixel"), Tausender-Stil und **Dezimal-Separator** (`.` vs `,`) des Records werden erhalten.
- **Berechnung:** `W × H` exakt aus `format_width/height`; `GP = W·H/1e9` auf 2 Dezimalen (Komma), `ROUND_HALF_UP`.
- **Beide Korruptionsrichtungen:** zu groß (uid 3: 2,50→0,25) UND zu klein (uid 531: 0,25→1,34).
- **Validierung pro Record:** aus dem NEUEN Text Maß+GP re-extrahieren → MUSS == truth; Prosa-Skeleton unverändert;
  sonst **SKIP + flag** (kein Write). Aktuell 0 Skips.
- **Idempotenz:** Guard = dims ≠ format_w×h → ein Re-Run überspringt bereits korrigierte.
- **Sicherheit (Write-Modus):** Backup (`uid|alt-value` → `dims_patch_backup.tsv`), transaktional (begin/commit/rollback).

Artefakte: `dims_patch_sample.txt` (Vorher/Nachher, 15 divers + 3 Beweisfälle) · `dims_patch_matchset.tsv` (alle 1.558).

## Sample-Beleg (Auszug)
```
uid 3:   2,50 Gigapixel (34055 × 73345 Pixel) → 0,25 Gigapixel (10783 × 23225 Pixel)
uid 4:   1,33 GP (60896 × 21826 Pixel)        → 0,25 GP (26412 × 9467 Pixel)
uid 5:   1,08 Gigapixel (77709 * 13911 px)    → 0,25 Gigapixel (37394 * 6694 px)
uid 289: 1,87-Gigapixel-Aufnahme (104502 × 17928 Pixel) → 0,25-Gigapixel-Aufnahme (38175 × 6549 Pixel)
uid 531: 0,25-…(31064 x 8049 Pixeln)          → 1,34-…(71840 x 18615 Pixeln)   [bidirektional kleiner→größer]
uid 7265:(0.14 Gigapixel) UNVERÄNDERT          [Punkt-Dezimal korrekt — nicht angefasst]
```

## VOLLER SEQUENZPLAN (jeder Write auf deinen Step-für-Step-GO, biz zuerst — DE ist live)
**biz:**
1. `patch_ai_de_dims.py --write` → patcht `ai_description_de` der 1.558 (Backup + transaktional). → behebt biz-DE-Seite.
2. `gigapixels:translate --language=es --fields=description` → **MD5 greift automatisch nur die 1.558**
   (geänderter source_hash) → ES-description-Rows neu aus korrigierter Quelle.
3. `es_desc_gate.py --db` Re-Gate → Maße byte-genau (1a=0).

**gmbh (nach biz-grün):**
4. `ai_description_de` der 1.558 **identisch patchen** (gmbh-DE-Seite). Dasselbe deterministische Skript gegen gmbh
   (oder Backup/Apply der 1.558 neuen DE-Werte) — eigener `--target gmbh`-Pfad.
5. **gmbh-ES = gezielter UPDATE der 1.558 bestehenden es-description-Rows** — **NICHT** `promote_es_catalog`
   (dessen Idempotenz-Guard bricht ab, gmbh hat schon 26.472 es-Rows). Kleines Skript:
   `UPDATE … SET value=<neuer biz-es-Wert>, source_hash=<neu> WHERE source_uid=? AND field='description' AND language='es'`
   für die 1.558 (transaktional, Verify == 1.558).
6. gmbh Cache-Flush → served-Recheck (Maße auf `/es/details/…` korrekt; DE-Seite auch).

**FR/RU** unangetastet (bereits korrekt). Die **137 no_dim** (HIST/GRAFIK ohne Maß) bleiben separate Entscheidung.

> Read-only. Kein DE-Source-Write / kein Re-Translate / kein gmbh-Write bis zu deinem GO.
