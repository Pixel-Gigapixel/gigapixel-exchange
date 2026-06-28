# ES Produkt-Beschreibungen (Teil C) — Dry-Run-Sample + Gate

**Lauf:** `gigapixels:translate --language=es --fields=description --dry-run --limit=50` (biz, Haiku, Delimiter-Contract)
**Quelle:** `ai_description_de` (Spalte) · **Ziel-Feld:** `description` · `source_hash`=MD5(ai_description_de) → Parität FR/RU
**Artefakte:** `sample.tsv` (uid·DE·ES, voll) · `desc_gate.txt` · `dryrun.log`. **Keine DB-Writes** (Dry-Run; `[desc]`-Print voll, nicht gekappt).

## Gate — 50 Records
| Check | Ergebnis |
|---|---|
| (1) **Zahlen byte-genau** (Multiset DE==ES) | **0 Abweichungen** ✓ (Hauptrisiko — Dezimalkomma `0,25`, Pixel-Maße, `GP` exakt) |
| (2) **Dimensions-Separator** (× vs x quellgetreu) | **0 Abweichungen** ✓ (uid 47 `11182 x 22383`, uid 48 `11182 × 22383` — beide quellgetreu) |
| (3) **IA-Konsistenz** (kein KI-Rest; `sin upscaling por IA`) | **0** ✓ |
| (4) **Fotograf/Eigenname verbatim** | **0 fehlend** ✓ (Daniel Richter / imageBROKER… erhalten) |

## (5) Fixed-Renderings vs. Voll-Korpus (8.889) — deine #2-Frage
Die fixen Renderings greifen auf der **realen** Phrasierung:
- `kein KI-Upscaling` **98%** · `keine KI-Generierung` **96%** · `Echte Kameraaufnahme` **89%**
- Anwendungen: `Spanndecke` 70% · `großformatige` 39% · `Messebau` 38% · `Messen` 2%
- Vertical: `Klinik` 355 · `Praxis` 17 · `Healing Environment` 16 → uid 47 zeigt treue Übersetzung
  („…diseño de consultorios y clínicas así como conceptos de healing environment").

→ **2–11% nutzen Varianten** (z. B. anderer Schlusssatz), die die fixen Formen NICHT exakt treffen — die
greift dann **Rule 5 (faithful/factual)** generisch ab. Im Sample war keine solche Variante auffällig;
falls du im Vollauf-Gate eine Variante als unsauber siehst, gezielter `--force`.

## Bewertung
Zahlen/Maße (das eigentliche Risiko über 8.870 Records) byte-genau, Separator quellgetreu, Eigennamen/Fotograf
erhalten, IA-Terminologie konsistent mit Trust-Box/Live-Site, Fixed-Renderings decken das Gros ab + generische
Treue für den Rest. **C-Sample ist abnahmereif.** Bei grün: `--fields=description` ohne Limit (Haiku, MD5-inkrementell).
