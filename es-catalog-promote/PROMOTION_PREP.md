# Schicht-2-Promotion (ES-Produktkatalog) biz → gmbh — READ-ONLY-Vorbereitung

Promotet die ES-Übersetzungen aus `tx_gigapixels_translation` (eigene Tabelle, NICHT im lang4-Site-Dump).
Ohne diesen Schritt ist der Katalog auf gmbh nur DE/EN — A+B+C ist erst danach käufer-sichtbar.

## Soll-Ist (read-only gelesen)
| | biz (Quelle) | gmbh (Ziel) |
|---|---|---|
| `tx_gigapixels_translation` es / **title** | **8.760** | **0** |
| es / **keywords** | **8.823** | **0** |
| es / **description** | **8.889** | **0** |
| **Σ es** | **26.472** | **0** → Idempotenz-Guard erfüllt |
| fr (title/kw/desc) | 8.751 / 8.798 / 8.870 | **identisch** (FR bereits promotet) |
| ru (title/kw/desc) | 8.761 / 8.824 / 8.870 | **identisch** |
| en (title/kw) | 6.078 / 8.735 | **identisch** |

## Risikopunkte — verifiziert
1. **Schema-Parität**: Spalten + Indizes von `tx_gigapixels_translation` biz==gmbh **identisch**
   (uid, source_table, source_uid, field, language, value mediumtext, source_hash, tstamp; kein pid/crdate).
   Das Skript bricht zusätzlich zur Laufzeit ab, wenn die Spaltenliste driftet.
2. **Produkt-uid-Identität** `tx_cartgigapixels_domain_model_gigapixel`: beide count(deleted=0)=**8.889**,
   max_uid=**9091**; Stichproben uid 1/100/5000/8889 → **identische sku+title** → `source_uid` löst auf
   gmbh dasselbe Produkt auf. (Gleiche DE-uid-Identität wie beim lang4-Dump.)
3. **uid wird gestrippt** (Ziel-AUTO_INCREMENT). Begründung: biz-es-uids sind die jüngsten Rows und würden
   mit dem gmbh-Bestand (en/fr/ru) auf dem PRIMARY kollidieren. Funktional egal — das FE-Lookup nutzt
   (source_table, source_uid, field, language), nicht uid. (FR/RU hatten zufällig uid-Gleichheit aus einem
   Full-Table-Copy; hier ist Strippen der sichere Weg.)

## Skript-Garantien (`promote_es_catalog.py`)
- Quelle IMMER biz; Ziel `--target gmbh`; `--dry-run` schreibt NICHTS.
- **Idempotenz-Guard**: Abbruch, wenn gmbh schon es-Rows hat.
- **Quell-Count-Guard**: Abbruch, wenn biz ≠ 8760/8823/8889.
- **Schema-Drift-Guard**: Abbruch bei Spalten-Mismatch.
- Transaktional (`begin`/`commit`/`rollback`, autocommit=OFF), batched (500).
- **Verify IN-TX vor Commit**: gmbh-es je field muss == 8760/8823/8889, sonst **Rollback** (kein Teil-Commit).

## Dry-Run (read-only, kein gmbh-Write) — siehe `dryrun.log`
```
biz es je field: title 8760 ✓ · keywords 8823 ✓ · description 8889 ✓
Quelle gelesen: 26472 es-Rows (erwartet 26472) ✓
DRY-RUN: würde 26472 Rows inserten (uid gestrippt) — KEIN Write
```

## Live-Promotion — Schritt für Schritt mit Daniels GO (Writes auf LIVE gmbh)
1. **GO** → `python3 promote_es_catalog.py --target gmbh` (transaktional, Verify-in-TX, Commit nur bei 3×Match).
2. **Verify-Output** prüfen (title/keywords/description == 8760/8823/8889 ✓).
3. **TYPO3-Cache auf gmbh flushen** (sonst greift FE-Cache nicht auf neue Übersetzungen).
4. **Served-Verifikation** auf gmbh: Produktdetailseite `/es/details/…` → Titel + Trust-Box-Labels (A) +
   Keywords + **Beschreibung** spanisch, 0 DE-Residue. Plus `/es/`-Katalogliste.

> Kein gmbh-Write ohne explizites Daniel-GO. Dieses Bundle ist read-only/dry-run.
