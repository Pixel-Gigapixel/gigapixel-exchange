# Glossar-Meta-Fix + Promotion biz→gmbh (Rev. 3)

## 1. Glossar-Meta-Fix (der konditionierte Befund)
**Root Cause:** Die Glossar-/Methodik-Seiten setzen `<meta name="description">` + og/twitter **programmatisch im
Controller** (`TermController`/`MethodologyController` via `MetaTagManagerRegistry`), NICHT aus dem pages-Record.
Beide hatten ein hartkodiertes `match($languageId)` mit cases nur für 1/2/3/4 (EN/FR/RU/ES) + `default` (DE) —
**5/6/7 (TR/PL/IT) fehlten → DE-Fallback.** Darum DE-Meta auf den Glossar-/Methodik-Seiten aller 3 Sprachen,
obwohl alle anderen Seiten (record-getrieben) korrekt lokalisiert waren.

**Fix:** cases 5/6/7 in alle 6 `match`-Blöcke ergänzt (TermController: title/desc, Breadcrumb-Label/Slug ×2,
Suffix; MethodologyController: title/desc, Slug). Strings via **glm-5.2:cloud** übersetzt. Diff:
`tooling-diffs/glossary_controllers.diff` (85 Zeilen). PHP-Lint grün (biz + gmbh).

**Page-Meta-Scan (Schritt 1) — Ergebnis:** DB-Page-Meta (pages.description/og/seo, 246 Felder × Sprache) war
bereits **0 DE** in IT/TR/PL — nur die controller-generierte Glossar-/Methodik-Meta war DE. Bestätigt: nicht
systematisch, nur diese 2 Seitentypen.

**Gate-Erweiterung (Schritt 3):** Die Page-Meta-Ebene fehlte im Gate. Jetzt zweifach abgedeckt:
- `site_postrun_gate.py` → neue Komponente **`page_meta`** (DB: description/og/seo, alle 107 Seiten/Sprache).
- `site_meta_gate.py` (NEU) → **Rendered-Meta-Gate**: scant served `<meta description>`/og/twitter/title der
  gerenderten Seiten (fängt controller-generierte Meta).

**Beleg DE-Residue Page-Meta = 0 (je Sprache):**
| | DB page_meta (246/Spr.) | Rendered-Meta (21 Seiten) |
|---|---|---|
| IT | DE_HI=0 EN_HI=0 ES_HI=0 | — |
| TR | DE_HI=0 EN_HI=0 ES_HI=0 | — |
| PL | DE_HI=0 EN_HI=0 ES_HI=0 | — |
| gesamt rendered | — | **DE_HI=0 EN_HI=0 ES_HI=0 → PASS** |

## 2. Promotion biz→gmbh (vollzogen)
Werkzeug: `promote_es_dump.py --target gmbh --lang {7,5,6}` (parametrisiert; Scoped-Copy, uid gestrippt,
Parent-Pointer = DE-uid identisch biz↔gmbh, je Sprache transaktional). **Integritäts-Check vorab:** alle von
biz-IT/TR/PL referenzierten DE-Parents existieren auf gmbh (pages/tt_content/term/category) — 0 fehlend.

Zusätzlich nach gmbh deployed: 18 XLIFF-Dateien (rsync) + beide Glossar-Controller (PHP-Lint grün). **Ein
Flush** (var/cache/code+data geleert + `typo3 cache:flush` exit 0).

**Verify nach Commit (gmbh, je Sprache):**
| Tabelle | IT | TR | PL |
|---|---|---|---|
| pages | 107 ✓ | 107 ✓ | 107 ✓ |
| tt_content | 237 ✓ | 237 ✓ | 237 ✓ |
| Glossar-Terme | 55 ✓ | 55 ✓ | 55 ✓ |
| Glossar-Kategorien | 7 ✓ | 7 ✓ | 7 ✓ |

(jeweils == biz-Quell-Count, Idempotenz-Guard hatte gmbh-Sprachstand vorher = 0 bestätigt.)

## 3. gmbh Live-Smoke (public, kurz — DEIN Served-Check ist die autoritative Prüfung)
Alle HTTP 200, korrektes `lang`-Attribut, lokalisierte Titel + Meta:
- `/it/` · `/it/glossario` (Meta „I termini chiave della vera fotografia gigapixel…") · `/it/privacy`
- `/tr/` · `/tr/soezluek` (Meta „Gerçek gigapiksel fotoğrafçılığının…") · 
- `/pl/` · `/pl/ochrona-danych`

→ **HALT für deinen cache-freien Served-Check (Glossar-Meta lokalisiert + Rechts/Landing/Checkout live +
DE/EN/ES=0 + Katalog-Regress).**
