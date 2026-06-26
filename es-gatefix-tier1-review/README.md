# Gate-Fix (gates.py G3 URL-aware) + 45/53-Redo — Review

## (4) gates.py G3 URL-Fix (NUR gates.py; G1/G2/Gsym/G&/Gcur + GER-Set unverändert)
Neu: `_strip_urls()` entfernt vor der DE-Residue-Prüfung https?://-URLs, www.… und bare Domains
(x.de/y, a.b.com/z) — nur innerhalb von german(). GER-Set, Schwellwerte, andere Gates unberührt.

### Re-Validierung
- UNIT: DE-Domain-Link → []  ·  echte DE-Prosa → weiterhin gefangen  ·  ES-Satz + DE-URL → []
- 45 (ES-Target mit deutsche-handwerks-zeitung.de-Link): uid 111 G3 jetzt **ok** (vorher FAIL)
- KONTROLLE (Target = DE-Quelle): G3 FAILt weiterhin auf ALLEN Prosa-Elementen → G3 NICHT geschwächt

## (3)/(5) 53 Ethik — Opus-Redo + Zitat-Handfix
- Angela-Davis-Zitat war auch unter Opus deutsch (Gate citation-exempt) → manuell auf ES gesetzt:
  „En una sociedad racista no basta con no ser racista. Hay que ser antirracista." – Angela Davis
  (Standard-Form; bitte Wortlaut gegenlesen). Re-gate: ALLE GATES GRÜN.
- ⚠️ ZWEITES DE-Zitat, uid 138: „Die Würde des Menschen ist unantastbar." (Grundgesetz Art. 1)
  — DEINE Entscheidung: übersetzen (wie Davis) oder als Original-Rechtszitat belassen? NICHT angefasst.

## 45 Presse — Opus-Redo
Mit gepatchtem Gate: PASS (22/22). URL ignoriert + uid-214-Zahlendefekt (Opus) behoben. Commit-bereit.

## Flow
gates.py-Diff reviewen → GO → ich committe gates.py (3. Tool-Commit) → dann 45+53 via --from-review.
53: vorher deine Entscheidung zum Grundgesetz-Zitat.
