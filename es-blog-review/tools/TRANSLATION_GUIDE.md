# TRANSLATION_GUIDE.md — gigapixel TYPO3 mehrsprachiger Rollout

**Zweck:** Destillat aller Regeln aus den ES-Batches (Agenturen→Innenarchitekten). Dient als
System-Prompt für den Übersetzer (Claude Code oder Modell-Call in `rollout.py`) und als
Referenz für `gates.py`. Gilt 1:1 für alle Zielsprachen (TR/PL/IT/AR …), nur die Sprachtoken
ändern sich.

Die **deterministischen** Prüfungen macht `gates.py` (Tag/Zahlen/Symbole/&amp;/Währung/DE-Reste).
Dieses Dokument deckt das ab, was ein Mensch/Modell beim **Erzeugen** der Übersetzung wissen muss.

---

## 0. Goldene Regel
Übersetze **nur Text zwischen den Tags**. HTML-Struktur, Attribute, Inline-Styles, Klassen,
`href`, Reihenfolge: **byte-identisch** übernehmen. Wenn `gates.py` G1 (Tag-Skelett) nicht grün
ist, wurde Struktur angefasst — Fehler, nicht „Stil".

> Tipp: Bei tabellen-/symbollastigen Elementen (z. B. ppi-`<table>` mit ✓/✗/⚠) **replace-basiert**
> aus der DE-Quelle bauen (nur die übersetzbaren Textfragmente ersetzen) statt von Hand neu tippen.

---

## 1. Byte-genaue Token (NIE verändern)
- **Zahlen & Maße:** jede Ziffer und jedes Trennzeichen exakt. Tausender/Dezimal **so lassen, wie
  sie dastehen** — pro Vorkommen. Beispiele real aufgetreten:
  - `$3,000` (US-Komma, **im englischen Zitat**) vs. `$3.000` (Punkt, in Prosa) — **beide** behalten.
  - `2.100 $`, `8,5 %`, `r = 0,09`, `r = 0,091`, `1.700+`, `93 millones de $`.
- **Prozent-/Maß-Spacing pro Vorkommen:** `75 %` (mit Space) und `75%` (ohne) können **im selben
  Cluster** beide vorkommen — exakt spiegeln. Ebenso `3–5 min` (en-dash) vs. `3-5 minutos`
  (Bindestrich) — je nach Quelle.
- **Fraktale D-Werte:** `D=1,3–1,5` (kein Space, en-dash), `D~1,6–1,7` (Tilde), `D = 1,3-1,5`
  (Spaces + Bindestrich) — **Notation pro Vorkommen** beibehalten.
- **Währung:** Symbol/Wort **verbatim, niemals umrechnen oder lokalisieren**. `$` bleibt `$`,
  `USD` bleibt `USD`, `€` bleibt `€`. (Gate `Gcur` vergleicht das Währungs-Token-Multiset.)
- **ppi / dpi:** als **englische Tokens** behalten. NICHT zu „ppp" o. ä. machen. ppi = echte
  Bildinformation, dpi = Druckerpunkte — **nie** vermischen.
- **Symbole:** `↑ ↓ ✓ ✗ ⚠ → ° ±` etc. byte-genau an Ort und Stelle. (Gate `Gsym`.)
- **HTML-Entities:** `&amp;` bleibt `&amp;` (nicht zu `&` oder `y`/`und` auflösen). (Gate `G&`.)
- **Marken/Eigennamen:** `Gigapixel GmbH`, `NatureLux`, Produktnamen — verbatim. „gigapíxel"
  (klein, lokalisiert) nur als **beschreibendes** Wort; die **Firma** bleibt `Gigapixel GmbH`.
- **Interne Links:** `href="/gigapixels"`, `/lizenzen`, `/kontakt`, `/auftragsarbeit` … bleiben auf
  den DE-Slugs (Link-Lokalisierung ist ein separater späterer Pass). Nur der **Linktext** wird übersetzt.
- **Fachbegriffe, die englisch bleiben:** `Evidence-Based Design (EBD)`, `Healing Environment`,
  `Prospect`, `Sensory Overload`, `Devices of Wonder`, `Tourist Gaze`, `Love of Place`,
  `Processing Fluency`, `Return on Investment`/`ROI`, `ADR`, `upscaling`, `burnout`, `stitching`,
  `EEG`, `HTML5`. (Konzept-Termini, die die DE-Quelle schon englisch führt.)

---

## 2. Zitate vs. Eigen-Claims — der wichtigste Unterschied
„…"-Spannen (deutsche Anführungszeichen, Schließzeichen meist `U+0022`) sind **zweierlei**:

1. **Wissenschaftliche Zitate** → **verbatim in Originalsprache**.
   - Englische Studienzitate/Titel (Ulrich, Salingaros, Interface, …): **englisch lassen**.
   - **Fremdsprachiges Zitat in Originalsprache lassen**, auch wenn das nicht die Zielsprache ist.
     Beispiel: das **deutsche** Rohe-et-al.-Zitat in Kliniken-394 bleibt **deutsch** (Zitat-Integrität;
     spiegelt das RU-Verhalten). → `gates.py` meldet das als **WARN „Fremdzitat? verifizieren"**,
     **kein Fehler**.
   - Studientitel/Journals/Autoren/Jahre/Bände (`Science, 224(4647), 420–421.`,
     `Nonlinear Dynamics 19(1)`): verbatim.
2. **Eigene Marketing-Claims** in „…" → **übersetzen** (sind keine Zitate!).
   - Real: 429 „Sehen Sie es vorher" → „Véalo de antemano"; 455 „Wir arbeiten evidenzbasiert"
     → „Trabajamos de forma basada en la evidencia".
   - **Falle:** Der DE-Reste-Gate strippt „…" standardmäßig — ein **nicht** übersetzter Claim würde
     dadurch *durchrutschen*. Deshalb: `gates.py --taglines <uids>` für Claim-Elemente angeben;
     der Tagline-Check prüft sie **ohne** Strip.

Faustregel: hat die „…"-Spanne eine **Quellenangabe** (Autor/Jahr/Journal) drumherum → Zitat
(Originalsprache). Ist es ein **Werbesatz** → übersetzen.

---

## 3. ASCII-Umlaut-Altlasten der DE-Quelle
Einige DE-Quellelemente (oft FAQ „Haeufige Fragen" / „In Kuerze") enthalten `ae/oe/ue/ss` statt
`äöüß` (`Haeufige`, `Staedte`, `ermoeglicht`, `Kuerze`). Das ist **Quell-Artefakt, kein Fehler**.
Die **Zielsprache** wird sauber geschrieben (korrektes Spanisch/Türkisch/…). `gates.py` führt diese
Tokens als DE-Marker → falls sie in der **Zielseite** auftauchen, ist das ein echter Leak.

---

## 4. Sprach-/Stilkonventionen (ES; analog je Zielsprache anpassen)
- es-ES Zahlenformat = DE-Format (Punkt Tausender, Komma Dezimal) → Ziffern bleiben ohnehin gleich.
- DSGVO → RGPD (sprachspezifische Rechtsbegriffe lokalisieren), aber Markennamen nicht.
- „Mio." (deutsche Abkürzung) → ausschreiben in Zielsprache („millones"), Zahl + `$` bleiben.
- FAQ-Anzahl **spiegeln** (4 DE-FAQs → 4 Ziel-FAQs). **Nicht** eigenmächtig eine 5. ergänzen — das
  bricht Tag-Skelett + Cross-Language-Parallelität. (Fehlende FAQs sind ein separates DE-Quell-Thema.)

---

## 4a. Präzisierungen (verbindlich — Große Zahlen, Quellenblöcke, Währungswörter)

- **Große Zahlen mit Skalenwörtern:** Ziffernfolge der QUELLE behalten, Größenordnung im Zielsprachen-WORT
  ausdrücken — Zahl NICHT umschreiben. DE „1,6 Milliarden" → ES „1,6 mil millones" (NICHT „1.600 millones").
  DE „2,5 Millionen" → ES „2,5 millones". So bleibt die Ziffernfolge prüfbar identisch; jede Abweichung ist
  dann ein echter Fehler.

- **Literatur-/Quellenblöcke** (z. B. `<p class="gp-blog-source">`): erklärende/beschreibende Sätze ganz normal
  ins Spanische übersetzen. NUR die bibliografische Referenz im Original lassen — Autor(en), Werktitel,
  Journal/Verlag, Jahr. Erklärender Fließtext im selben Block ist KEIN Zitat und MUSS übersetzt werden.

- **Währungen:** Beträge, Symbole, ISO-Codes byte-genau (3.000, $, USD, €). Währungs-WÖRTER übersetzen:
  „Dollar" → „dólares", „Euro" → „euros". Gilt auch in Titel/Slug/SEO-Feldern.

- **„KI"** (Künstliche Intelligenz) → spanisch „IA". Compounds: „KI-Upscaling" → „escalado por IA".
  `KI` bleibt in KEINER Zielsprache deutsch (gate-enforced via G3).

- **Inhalts-Zitate und Fachbegriffe** in die Zielsprache übersetzen (z. B. Adobe-Zitate, „Weißpunkt" →
  „punto blanco", „Punktzuwachs" → „ganancia de punto"). NUR bibliografische Referenzen
  (Autor/Titel/Journal/Jahr) bleiben original.

- **Zitierter SATZ aus einer Quelle** (z. B. ein Adobe-Help-Center-Satz) ist INHALT und wird in die
  Zielsprache übersetzt. Nur die bibliografische REFERENZ bleibt original: Autorennamen, Werk-/Journaltitel,
  Verlag, Jahr, Referenzmarker wie (Q1). Ein fremdsprachiger Satz in Anführungszeichen auf der Zielseite
  ist ein Defekt.

- **Zeit-Idiome ziffernfrei**: „rund um die Uhr" → „a todas horas" / „ininterrumpidamente" — KEINE Zahl
  („24") einfügen, die in der Quelle nicht steht (sonst Zahl-Gate-Bruch).

- **Blog-Meta-Zeile** (`<p class="gp-blog-meta">`): Datum UND Kategorie in die Zielsprache lokalisieren —
  Datum im zielsprachlichen Format (ES: „13 de marzo de 2026", nicht „13. März 2026"), Monatsnamen
  und Kategorie-Label übersetzt. Die Meta-Zeile ist KEIN Zitat.

---

## 5. Pflicht-Gates vor jedem INSERT (`gates.py`)
```
python gates.py <DE_payload.json> <ZIEL_payload.json> [--taglines <uids>]
```
Grün heißt: **G1** Tag-Skelett identisch · **G2** Zahlen-Multiset identisch · **Gsym** Symbole
identisch · **G&** &amp;-Anzahl identisch · **Gcur** Währungs-Token identisch · **G3** keine
DE-Funktionswörter in echter Prosa. WARN (in-quote-DE) = Fremdzitat verifizieren. Exit 0 = go.

> `gates.py` nutzt bewusst nur **eindeutige** DE-Marker (kein in/an/am/so/war/man/die), damit
> englische Titel wie „Stories in the Rock" oder „zoom in" nichts auslösen.

---

## 6. INSERT-Mechanik (gilt sprach-/seitenübergreifend)
Pro Element **die Strukturzeile klonen**, dann nur Sprache + Text überschreiben:
- `sys_language_uid = <ziel>` (ES=4)
- `l18n_parent = <de_uid>` **(NICHT l10n_parent — das ist das pages-Feld)**
- `l10n_source = <de_uid>`
- `pid = <seiten-pid>`
- `header / subheader / bodytext` = Ziel-Werte (byte-genau)
- **FAL-Bildreferenzen / colPos / sorting / pi_flexform** kommen aus der **Klon-Vorlage**.

**Klon-Vorlage wählen:**
- **RU-Overlay vorhanden** → RU-Zeile (`ru_uid`) klonen. RU-Match **immer über (pid, colPos,
  sorting)**, **nie** JOIN auf l18n_parent (false-negatives). *(Blueprint #4)*
- **Kein RU-Overlay (`ru_uid=null`)** → **DE-Quellzeile selbst** (gleiche uid) als Donor klonen,
  dann Sprache/Parent/Text überschreiben. FAL/flexform/colPos/sorting kommen so direkt aus dem
  DE-Original. *(Mirror-RU-Ausnahme #5)* Quell-Sprachlücken (z. B. Home) trotzdem übersetzen.

**Nach dem INSERT:** die **13 `cache_*`**-Tabellen TRUNCATEn (nicht `cf_*`).

**Pflege je Sprache (einmalig, vor Promotion):**
- `logo-<iso>.svg` **muss existieren** (sonst blankt `f:image`+contentObjectExceptionHandler den
  ganzen Body **still**). Body-Canary pro Sprache obligatorisch — „Title-grün ≠ Content-grün".
- LanguageMenu (`lib.languageMenu special.value`) um die Sprache erweitern.
- `plugin.tx_cart` / `tx_cart_countries` Sprach-Block ergänzen (sonst Cart in DE).
- `config/sites/main/config.yaml`: Sprachblock auch im **Repo** (für gmbh-Promotion).

---

## 7. Per-CType-Hinweise
- **textmedia:** Standardfall (Body in `bodytext`, Bilder via FAL). 95 % der Elemente.
- **menu_subpages / menu_*:** kaum/kein `bodytext`; übersetzbar ist v. a. `header` (+ ggf.
  Menü-Titel der Zielseiten, die separat als pages-Overlays laufen). Struktur/Menükonfig vom Donor.
- **list (Plugin):** enthält `pi_flexform` — übersetzbar sind nur Label-/Text-Felder darin;
  Plugin-Keys/Schalter unverändert vom Donor übernehmen. Flexform als XML behandeln, Tag-Skelett wahren.

---

## 8. Schnell-Checkliste (vor jedem Batch)
- [ ] Quelle commit-pinned gezogen, Element-/Feldzahl verifiziert
- [ ] Währung/Symbole/Entities/„…" im Payload gescannt (was muss verbatim?)
- [ ] Übersetzt: nur Text, Struktur unangetastet
- [ ] Fremdzitate (EN **und** ggf. andere Sprachen) verbatim; Eigen-Claims übersetzt
- [ ] `gates.py … --taglines <uids>` → alles grün, WARNs verifiziert
- [ ] INSERT: l18n_parent/l10n_source=de_uid, sys_language_uid, pid, richtige Klon-Vorlage
- [ ] 13 `cache_*` truncaten
- [ ] tatsächlichen Ziel-Slug aus pages-Overlay melden (nicht annehmen)
