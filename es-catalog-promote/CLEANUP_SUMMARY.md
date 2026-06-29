# TR/PL/IT Residual-Cleanup (biz) — abgeschlossen

| Sprache | echte Dims (patch_text, kein Haiku) | empty/de_res/pad re-translate | Re-Gate (nach Cleanup) |
|---|---|---|---|
| **TR** | 4 | 4 (→ Found/Written 4) | empty 0 · de_res 0 · **real-dims 0** · pad 2 · num 11=benign |
| **PL** | 2 | 8 (→ Found/Written 8) | empty 0 · de_res 0 · **real-dims 0** · pad 2 · num 19=benign |
| **IT** | 3 | 6 (→ Found/Written 6) | empty 0 · de_res 0 · **real-dims 0** · pad 1 · num 17=benign |

- **empty/de_res = 0** über alle 3 (gelöscht + sauber re-translated; Coverage intakt 8760/8823/8889 je Sprache).
- **echte Dims-Fehler = 0** (die je Sprache gefundenen deterministisch via patch_text aus format_w×h gefixt, KEIN Haiku).
- **num-Rest (11/19/17) = benigne** Zahl-Differenzen: Tausender-/Dezimal-Separator-Normalisierung auf Zielsprache
  („70.000"→„70000", „0.11"→„0,11"/„0,11"). KEINE Wert-Korruption (real-dims-Fehler=0 verifiziert).
- **pad-Rest (2/2/1) = minor** Haiku-Keyword-Padding bei ultrakurzen Listen (Re-Force würde nondeterministisch re-padden;
  vernachlässigbar, ~2 Records/Sprache).

Samples (15 gemischt, inkl. gepatchte/re-translated) + Re-Gate je Sprache: catalog-{tr,pl,it}/.
→ HALT. Reviewe Terminologie/Maße/Residue an den echten Daten, dann gmbh-Promotion.
