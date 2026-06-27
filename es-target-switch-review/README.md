# --target-Switch (rollout.py + glossar_load.py) — Review, KEIN Commit

## Zweck
Beide Tools wählen das Ziel-System env-getrieben via `--target {biz,gmbh}` (Default **biz**=Staging).
Ohne --target trifft ein Lauf NIE Live. Für Schritt 2 der Promotion (ES-Content auf gmbh).

## rollout.py.diff (5 Hunks)
1. Modul-Global `TARGET = "BIZ"` (statt hartkodierter BIZ_*-Nutzung); Doku der Env-Konvention.
2. `_conn()`: `host=os.environ[f"DB_{TARGET}_HOST"]` … (DB_{TARGET}_HOST/USER/PASSWORD/NAME)
3. `flush_cache()`: `_require_env(f"{TARGET}_SSH"/…_SSH_PORT/…_APP_ROOT)` + `{TARGET}_PHP` (Default php82.bin.cli)
4. argparse: `--target {biz,gmbh}` default biz → setzt `global TARGET = a.target.upper()`
5. Lauf-Log zeigt `target=GMBH [LIVE]` (Sicht-Sicherheit bei jedem Lauf)

## glossar_load.py (produktioniert aus dem getesteten Scratchpad-Stand)
- `--target {biz,gmbh}` (Default biz) + `--review-dir` (Default ~/exports/es-glossar-review)
- `db(TARGET)`: `DB_{TARGET}_*`; Idempotenz-Guard (bricht ab, wenn lang4 schon da)
- Insert-Recipe unverändert (55 Terme lang4 l10n_parent=DE-uid + 7 Kat-Overlays + 2 Plugin-Elemente)
- normalize() gigapíxel/Gigapixel unverändert; reviewte term-*.json bleiben Source-of-Truth
- Cache-Flush via `rollout.flush_cache` (TARGET-aware, DRY)

## Eigenschaften zur Abnahme
- **NULL hartkodierte gmbh-/biz-Infra-Werte** — alles `os.environ[f"DB_{TARGET}_…"]` / `_require_env(f"{TARGET}_…")`
- Default biz → ohne --target identisches Verhalten wie bisher (kein Regress; py_compile + --help grün)
- de_uid-Identity biz↔gmbh (bestätigt) → l10n_parent/l18n_parent greifen 1:1, kein Re-Keying

## .env.local (Werte setzt DANIEL, nie CC/plaintext)
DB_GMBH_HOST/USER/PASSWORD/NAME + GMBH_SSH=gigapx@dedi1178.your-server.de + GMBH_SSH_PORT=222
+ GMBH_APP_ROOT=/usr/www/users/gigapx/deploy/app  (+ optional GMBH_PHP)
