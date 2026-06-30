# Site-Schicht IT / TR / PL — Review-Bundle D (biz)

**Stand:** 2026-06-30 · **Ziel-System:** biz (Staging) · **Übersetzungs-Engine:** cloud-Ollama `glm-5.1:cloud` (NICHT mehr Sonnet/Haiku) · **HALT für Daniel-Review + EIN gmbh-GO.**

Dieses Bundle deckt die komplette Site-Schicht für Italienisch (langId 7), Türkisch (5) und Polnisch (6):
pages-Overlays, tt_content, Glossar (Terme + Kategorien), XLIFF-UI-Strings, meta-keywords, Struktur-Overlays.
**Kein gmbh-Write erfolgt.** Promotion erst nach deinem GO.

## Ergebnis auf einen Blick

| Komponente | IT | TR | PL | Quelle/Ref |
|---|---|---|---|---|
| pages-Overlays | 105 | **107** | 106 | ES=107 |
| tt_content | 235 | 237 | 236 | ES=232 |
| Glossar-Terme | 55 | 55 | 55 | DE=55 |
| Glossar-Kategorien | 7 | 7 | 7 | DE=7 |
| XLIFF-Keys (6 Dateien) | 361 | 361 | 361 | en-source=361 |
| **Postrun-Gate** | **PASS** | **PASS** | **PASS** | DE_HI=0 & EN_HI=0 & ES_HI=0 |

Gerenderte Seiten (biz, served HTML, alle HTTP 200, `lang`-Attribut korrekt, 0 DE/EN/ES-Leak im Body):
Startseite · /bilder-verkaufen · Checkout (/cart) · Glossar — je Sprache → `rendered/`.

## Wichtigster Befund: Spanisch-Leak (behoben)

`rollout.py:555` (Gate-Retry-Feedback) war hartkodiert auf **„übersetze … ins Spanische"**. Beim
„noch-DEUTSCH"-Retry hat das Modell (sowohl der frühere Sonnet-Lauf ALS AUCH glm) ganze Seiten-Inhalte
**ins Spanische** statt in die Zielsprache übersetzt. Der bestehende DE/EN-Gate fing das nicht (Spanisch
ist weder Deutsch noch Englisch). Verstärkt wurde es dadurch, dass `TRANSLATION_GUIDE.md` mit spanischen
Beispielen geschrieben ist → glm driftet bei langem Content ins Spanische.

**Umfang (vor Repair):** TR ~56, IT ~73, PL ~77 tt_content-Elemente waren spanisch (ganze Seiten wie
Datenschutz/Impressum, Tier-2-Landingpages, Blog).

**Fixes:**
1. `rollout.py:555` parametrisiert auf die Zielsprache (`humanize_gate_feedback(..., lang)`).
2. Zielsprachen-Anker oben im System-Prompt + Anti-Spanisch-Direktive in `translate_fields`.
3. Neuer **ES_HI-Tier** im Gate (`site_gate.py`) — diese Fehlerklasse wird ab jetzt erkannt
   (FP-sicher: kurze Tokens wie `el/para/las` raus, da echte TR-/PL-Wörter „Hand/Geld/Wald").
4. Repair: betroffene Seiten neu übersetzt (Dry-Run --force → gate-/sprach-verifiziert → alte Overlays
   soft-delete → from-review insert). **Ergebnis: ES_HI=0 in allen drei Sprachen.**

Details + Zahlen: `FINDINGS.md`.

## Offene Punkte (HALT — deine Entscheidung)

3 harte Content-Seiten konnten von glm nicht gate-grün übersetzt werden und rendern aktuell via
**DE-Fallback** (`fallbackType: fallback` ist site-weit aktiv → Seite funktioniert, zeigt deutschen Text):

| pid | Sprache | Grund |
|---|---|---|
| 138 | IT | HTML-Tag-Skelett-Mismatch (uid 548) — glm verändert Tags |
| 371 | IT, PL | Zahl-/Token-Mismatch „24/7" / „KI" (uid 799) — historisch nur von Opus gelöst |

Empfehlung: Guide-Regel für „rund um die Uhr → ziffernfrei" auf IT/TR/PL erweitern, oder diese 2 Seiten
manuell. **Per glm-only-Vorgabe NICHT an Sonnet/Opus eskaliert.**

Große Legal-Seiten (Impressum/Datenschutz) waren grenzwertig (glm liefert bei >10k-Token-Eingaben teils
leere Antworten) — wurden in Repair-Runde 2 mit gehärtetem Prompt aber **grün** (siehe Gate).

## Verzeichnis

- `rendered/` — 12 gerenderte biz-Seiten (HTML, served, Basic-Auth-gerendert)
- `gate/` — Postrun-Gate je Sprache (DE_HI/EN_HI/ES_HI = 0) + Glossar-Render-Beispiele
- `xliff-sample/` — XLIFF-Stichprobe (12 trans-units je Sprache) + XLIFF-Gate
- `tooling-diffs/` — Diffs (`rollout.py`, `glossar_load.py`) + neue Tools (`site_gate`, `xliff_translate`,
  `site_postrun_gate`, `structural_overlay`, `repair_es_leak`, `force_commit_clean`)
- `INVENTORY.md` — Inventar-Abgleich (Gap) · `FINDINGS.md` — Spanisch-Leak im Detail · `SHA256SUMS`
