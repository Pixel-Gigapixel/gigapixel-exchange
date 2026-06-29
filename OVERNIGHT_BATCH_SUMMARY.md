# Übernacht-Batch — Abschlussbericht (biz, unbeaufsichtigt)

## A — Sofort (deterministisch, biz+gmbh) ✓
- **A1 EN-Dims-Fix:** `patch_ai_de_dims.py --column ai_description_en --write` auf biz + gmbh → je **1.816** Records,
  Re-Gate **0 falsche Maße** auf beiden DBs. EN-Seiten/Karten/Schema-Maße jetzt korrekt.
- **A2 Pre-wire TR/PL/IT/AR:** 6 Render-Spots (HEAD + `5=>tr,6=>pl,7=>it,8=>ar`, photographer-frei) auf biz+gmbh
  deployed + Flush. Inert/crash-frei bis DB-Rows da sind.

## B — TR/PL/IT Katalog B+C auf biz ✓ (A=UI-Labels-XLF NICHT Teil dieses Command-Laufs)
Prompts als faithful Mirror der ES-Prompts (Ziel-Terminologie eingefroren) + Dispatch-Cases (NICHT default→FR).
Sample-Gate-then-Full (catalog_sample_gate.py): alle 3 **Sample-GREEN** → Voll-Lauf.

| Sprache | title | keywords | description | Sample-Gate | Voll-Post-Run-Flags (ES-Residual-Klassen) |
|---|---|---|---|---|---|
| **TR** | 8.760 | 8.823 | 8.889 | GREEN | empty 66 · de_res 2 · num 15 · pad 2 |
| **PL** | 8.760 | 8.823 | 8.889 | GREEN | empty 68 · de_res 4 · num 21 · pad 2 |
| **IT** | 8.760 | 8.823 | 8.889 | GREEN | empty 67 · de_res 3 · num 18 · pad 2 |

Stichproben verifiziert sauber (z. B. TR „gigapiksel çekimi", PL „zdjęcie gigapikselowe", IT „ripresa gigapixel",
Maße byte-genau, Fixed-Renderings greifen, kein DE/EN-Residue). Gate-Reports + Samples: `catalog-{tr,pl,it}/`.

## Post-Run-Flags = bekannte ES-Residual-Klassen (deterministisch fixbar in der beaufsichtigten Runde)
- **num** (15–21/Sprache): Desc-Maße ≠ DE-Quelle = Haiku-Byte-Halluzination (~0,2%) → `patch_text` auf die
  jeweiligen `<lang>`-desc-Rows (truth=format_w×h, KEIN Haiku) — exakt wie der ES-2-Record-Fix.
- **empty** (66–68): kw/desc-Skips → gezielter `--force` der uids.
- **de_res** (2–4): einzelne untranslated Fixed-Phrase → gezielter `--force`.
(Sample-Gate war GREEN → Voll-Lauf korrekt gefahren; Post-Run-Flags sind Feinschliff, kein Stopp-Signal.)

## NICHT übernacht (deine beaufsichtigte Rückkehr)
- **gmbh-Promotion TR/PL/IT** (Live; nach deinem biz-Review) — `promote_es_catalog.py` generalisieren auf `--lang`.
- **Residual-Cleanup** der num/empty/de_res je Sprache (deterministisch, s. o.).
- **AR** (RTL/nicht-lateinisch, Runbook-Fallstrick 7 — Prompts + Gate gesondert).
- **Site-Ebene/config** je Sprache (langId-Block, LanguageMenu, logo …) + manuelle XLIFFs (A-Labels, Form, Checkout …).
- **Served-Checks** (deine web_fetch/Browser).
