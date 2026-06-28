# ES Beschreibungen (Teil C) — Post-Run-Gate über die volle Menge (8.889)

**Lauf:** `--language=es --fields=description` (ohne Limit, Haiku, MD5-inkrementell, Delimiter-Contract) → **8.889 geschrieben**.
**Gate:** `es_desc_gate.py --db` (liest ungekappte ES aus `tx_gigapixels_translation`, DE aus `ai_description_de`).
**Artefakte:** `desc_postrun_gate.txt` (Roh) · `flagged_postrun.tsv`.

## Skalen-Checks
- **(0) Coverage:** DE-Beschreibung (deleted=0) ohne es-Row = **0** ✓
- **(0b) Leere es-description trotz DE (Trunc/Skip-Fänger):** **0** ✓ → kein Truncation-Verlust bei der 8000-Token-Prosa.

## Risiko-Checks (roh → triagiert)
| Check | roh | echt | Bewertung |
|---|---|---|---|
| (1a) **Ziffernkorruption** (DE-only UND ES-only) | 5 | **1** | **uid 2309**: DE `12507` → ES `21507` (Dimensions-Swap) = der eine echte #1-Risiko-Treffer. Die 4× `1950→50` sind das korrekte Idiom „años 50". |
| (1b) Zahl-Drop (eine Seite) | 9 | 0 | Jahrhundert→römisch („16. Jahrhundert"→„siglo XVI") + Tausender-Normalisierung — alles korrekt. |
| (2) Separator × vs x | 24 | kosmetisch | Modell normalisierte Quell-`x` → `×`. Wert/Ziffern unberührt. |
| (3) **IA-Casing** | 27 | **27** | „sin upscaling por **ía**" statt „por **IA**" (Akronym klein+akzentuiert). Chirurgisch fixbar: `"por ía"`→`"por IA"` (eindeutig; blankes `ía`-Replace verbietet sich wegen „fotografía"). |
| (4) Fotograf | 239 | ~0 | **Gate-Artefakt**: Regex matcht „Foto/Aufnahme von [Motiv]" (Motiv≠Fotograf). Echter Fotograf durchweg erhalten („Fotografiado por Daniel Richter"). Check für Descriptions unbrauchbar. |

## Zahlen byte-genau — das Kernergebnis
Über **8.889** Records genau **1** echte Ziffernkorruption (uid 2309) = **0,011 %**. Der Delimiter-Contract + Regel 1
(byte-genau) haben über die volle Skala gehalten — genau der Punkt, den die 50er-Stichprobe nicht garantieren konnte.

## Empfohlene gezielte Remediation (auf dein GO)
1. **uid 2309** — es-description löschen + `--force` re-translate (1 Record). Danach Zahl-Recheck.
2. **27× „por ía"→„por IA"** — chirurgischer transaktionaler UPDATE `REPLACE(value,' por ía',' por IA')`
   auf die 27 (deterministisch, kein Re-Translate-Risiko nondeterministischer Re-„ía").
   Alternativ Prompt-Härtung „write the acronym IA in uppercase" + Re-Force — aber der UPDATE ist sauberer.
3. (2)/(4) = kein Handlungsbedarf (kosmetisch / Artefakt).

Nach (1)+(2): Re-Gate → (1a)=0, (3)=0 → **C final**. Korpus-Coverage der Fixed-Renderings unverändert
(89–98%, Rest generisch via Rule 5).
