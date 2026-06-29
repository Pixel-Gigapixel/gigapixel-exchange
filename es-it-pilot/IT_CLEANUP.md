# IT-Cleanup — DE-Stray-Token-Body-Leaks (biz+gmbh, abgeschlossen)

## Loop
1. `cleanup_catalog_lang.py --lang it --stage prep` → 37 (uid,field) gelöscht (de_tok 36 + pad 1), num-patched=0 (17 num benign).
2. `gigapixels:translate --language it --fields=description,keywords` (biz) → 37 neu. de_tok 36→15.
3. **15 = 3 FP + 12 echte:** `Reichstagsgebäude` (Eigenname → Gate-Fix `\bGebäude\b`) · 12× `ultrahochauflösend` (Haiku-persistent).
4. **Deterministischer Ersatz** `ultrahochauflösend(e)` → `ultra-alta risoluzione` (= Term der 6 erfolgreichen Korpus-Records; zero-residue verifiziert). 12 biz-patch.
5. biz→gmbh-Sync 37 divergierte Rows (in-TX-Verify de_tok=0) + gmbh cache:flush.

## Verifikation
- biz de_tok=0 · gmbh de_tok=0 (in-TX vor Commit).
- Live gmbh `/it/details/ein-typischer-strassenzug-in-dublin`: 200, `ultrahochauflösend`=0, gerendert „Ripresa fotografica **ultra-alta risoluzione** per stampe dettagliate di grande formato."
- /en/-Dims: 0 Mismatch biz+gmbh (spotcheck uid1 60896×21826 ✓, uid2 31064×8049 ✓).

## Before/After (12, alle zero-residue)
- uid 560 [description]
  - ALT: Ripresa fotografica ultrahochauflösende per stampe dettagliate di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione per stampe dettagliate di grande formato.
- uid 1065 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1066 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1067 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1068 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1069 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1070 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di frutta per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1071 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di agrumi per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di agrumi per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1072 [description]
  - ALT: Ripresa fotografica ultrahochauflösende di agrumi per controsoffitti tesi e decorazione dello spazio interno di grande formato.
  - NEU: Ripresa fotografica ultra-alta risoluzione di agrumi per controsoffitti tesi e decorazione dello spazio interno di grande formato.
- uid 1354 [description]
  - ALT: Fotografia gigapixel ultrahochauflösende di un pavimento in sughero in 1,42 Gigapixel (61152 × 23202 pixel).
  - NEU: Fotografia gigapixel ultra-alta risoluzione di un pavimento in sughero in 1,42 Gigapixel (61152 × 23202 pixel).
- uid 1355 [description]
  - ALT: Fotografia gigapixel ultrahochauflösende di un pavimento in sughero in 2,77 Gigapixel (61152 × 45368 pixel).
  - NEU: Fotografia gigapixel ultra-alta risoluzione di un pavimento in sughero in 2,77 Gigapixel (61152 × 45368 pixel).
- uid 1356 [description]
  - ALT: Fotografia gigapixel ultrahochauflösende di un'orchidea in 1,44 Gigapixel (30040 × 47873 pixel).
  - NEU: Fotografia gigapixel ultra-alta risoluzione di un'orchidea in 1,44 Gigapixel (30040 × 47873 pixel).
