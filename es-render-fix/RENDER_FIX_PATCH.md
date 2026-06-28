# Render-Fix Patch — langId 4 → 'es' (+ ru-Schema-Altbug)

Scope (b): ES-Mapping in den 4 Stellen + der `ru`-Altbug in SchemaViewHelper. Reiner Code-Change, keine DB.
**ES-Änderung und ru-Altbug getrennt gelabelt.** PHP lint: alle 3 ViewHelper sauber.

## 1) DisplayTitleViewHelper.php — [ES] (H1 / Teaser / Liste / Suche)
```diff
             1 => 'en',
             2 => 'fr',
             3 => 'ru',
+            4 => 'es',          # [ES]
             default => 'en',
```

## 2) OgTagsViewHelper.php — [ES] (og:title / og:description)
```diff
             1 => 'en',
             2 => 'fr',
             3 => 'ru',
+            4 => 'es',          # [ES]
             default => 'de',
```

## 3) SchemaViewHelper.php — [ES] + [RU-ALTBUG]
```diff
             1 => 'en',
             2 => 'fr',
+            3 => 'ru',          # [RU-ALTBUG] — fehlte hier (Schema war für RU schon 'en')
+            4 => 'es',          # [ES]
             default => 'en',
```

## 4) Show.html (dg_theme, Plugins/Gigapixel) — [ES] (Beschreibungs-Block)
```diff
-						<f:if condition="{currentLanguageId} == 2 || {currentLanguageId} == 3">
+						<f:if condition="{currentLanguageId} == 2 || {currentLanguageId} == 3 || {currentLanguageId} == 4">   # [ES]
 							<f:then>
-								<f:variable name="langCode"><f:if condition="{currentLanguageId} == 2"><f:then>fr</f:then><f:else>ru</f:else></f:if></f:variable>
+								<f:variable name="langCode"><f:switch expression="{currentLanguageId}"><f:case value="2">fr</f:case><f:case value="3">ru</f:case><f:case value="4">es</f:case></f:switch></f:variable>   # [ES] sauberer switch statt 2-vs-else
 								<f:variable name="translatedDesc">{dg:productTranslation(uid: gigapixel.uid, field: 'description', language: langCode)}</f:variable>
```
> Der `langCode`-Block wurde von „2→fr / else→ru" auf einen `f:switch` (2→fr, 3→ru, 4→es) umgestellt —
> sonst hätte ES via `else` fälschlich `ru` bekommen.

---

## ⚠️ ACHTUNG — Show.html trägt eine VORBESTEHENDE, NICHT von mir stammende Änderung
Der Working Tree hatte Show.html schon vor diesem Fix modifiziert (Session-Start-`git status`). Diese Hunks
gehören NICHT zum Render-Fix, sondern zur **Fotografen-Link-Arbeit (gigapixels_visualsearch)**:
```diff
+    xmlns:vs="http://typo3.org/ns/Gigapixel/Visualsearch/ViewHelpers"
...
-									<small> <f:format.crop maxCharacters="275">
+									<small> <vs:photographerLink photographer="{gigapixel.photographer}"><f:format.crop maxCharacters="275">
 											<f:format.nl2br>{gigapixel.photographer}</f:format.nl2br>
-										</f:format.crop></small>
+										</f:format.crop></vs:photographerLink></small>
```
**Risiko:** Ein Deploy von Show.html zieht diese `vs:photographerLink` mit. Wenn der `vs:photographerLink`-
ViewHelper (gigapixels_visualsearch) auf biz/gmbh **nicht** deployed ist, **crasht** die Produktseite (unbekannter ViewHelper).

**Brauche deine Entscheidung vor dem Show.html-Deploy:**
- (a) Show.html as-is deployen (inkl. photographerLink) — nur wenn der vs-ViewHelper auf biz+gmbh schon live ist; oder
- (b) NUR den langId-4-Hunk deployen, den photographerLink-Hunk vorerst rauslassen (ich erzeuge eine isolierte Show.html); oder
- (c) du sagst, der photographerLink ist Teil eines anderen, bereits laufenden Deploys → dann (a).

Die 3 ViewHelper sind sauber (nur mein Diff) und unkritisch — die kann ich unabhängig deployen.
