# Dims-Patch biz (Schritt 1-3) — Re-Gate-Ergebnis (HALT vor gmbh)

## Ausgeführt (biz Staging)
1. `patch_ai_de_dims.py --write`: Backup (dims_patch_backup.tsv, 1558) + transaktional → **COMMIT 1558** ai_description_de gepatcht.
2. `gigapixels:translate --language=es --fields=description`: „Found 1558" → **✓ Written 1558** (MD5 zog nur die geänderten).
3. Re-Gate (`es_desc_gate.py --db`) + gezielte dims-Verifikation über die 1558.

## Ergebnis
- **DE-Maß == echte Datei (format_w×h): 1557/1558 korrigiert.**
  - Ausnahme **uid 9090**: `format_width×height = 0×0` ("no file found") → unpatchbar, pre-existing Daten-Gap (Bild fehlt).
- **ES-Maß == truth: 1555/1558.** Rest:
  - **uid 4578** — ES-Re-Translate-Byte-Fehler: Höhe 11973 → **4724** (Breite 20878 korrekt). DE korrekt.
  - **uid 2309** — ES-Re-Translate-Byte-Fehler: Höhe 20182 → **21826**. DE korrekt.
  - uid 9090 — 0×0, nicht beurteilbar.
  → Gate (1a) ECHTE Ziffernkorruption = **2** (genau 4578, 2309). Gleiches Haiku-Halluzinations-Muster wie der ursprüngliche C-Lauf.
- Coverage 0, leer 0. (2) Separator / (4) Fotograf = bekannte Artefakte.

## Empfehlung
- **uid 4578 + 2309:** gezielter Re-Force (es-row löschen → 1 Record re-translate), dann dims-Recheck — wie beim ursprünglichen uid-2309-Fix.
- **uid 9090:** separat (Bild/Datei fehlt; nicht Teil des Dims-Fixes).
- Danach biz dims-grün → gmbh (Schritt 4-6) auf separaten GO.

> HALT — kein gmbh-Write bis zu Daniels biz-Review.

---
## UPDATE — biz dims-grün (nach deterministischem 2-Record-Fix)
- uid 4578 + 2309 via `patch_text` auf die ES-Row (kein Haiku) gefixt: Höhe 4724→11973 bzw. 21826→20182;
  Prosa byte-identisch, Validierung (Maß/GP/Skeleton) ok, Backup `dims_es2_backup.json`.
- Re-Gate über die 1.558: **DE-Maß ≠ truth = 0 · ES-Maß ≠ truth = 0 · Gate (1a) = 0** · Coverage 0 / leer 0.
- **biz dims-grün (DB).** uid 9090 (0×0, fehlendes Bild) bleibt separater Missing-File-Punkt.
- Nächster Schritt: gmbh (4–6) auf Daniels GO — Schritt 5 zieht die KORRIGIERTEN biz-es-Werte (inkl. der 2).
