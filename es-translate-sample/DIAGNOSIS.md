# ES Produkt-Übersetzung — Sample-Review (Teil B: title + keywords)

**Lauf:** `gigapixels:translate --language=es --fields=title,keywords --limit=50 --dry-run` (biz)
**Umfang:** 50 Records / 100 Felder · Modell = DEFAULT (Sonnet) im Dry-Run · Vollauf wäre Haiku, MD5-inkrementell
**Artefakte:** `sample.tsv` (uid · field · DE · ES) · `gate_report.txt` · `dryrun.log`
**Hinweis:** Der Dry-Run-Print kappt Werte auf 60 Zeichen — Titel quasi vollständig, **Keywords als Preview**.

---

## Gesamturteil

- **Titel: exzellent.** Treu, idiomatisch, Eigennamen erhalten (Ahornboden, Karwendel, BMW, Schloss Belvedere,
  Spree, St. Johann Nepomuk), Geo übersetzt (Múnich, Baviera, Irlanda), `freigestellt → recortado`,
  Akzente korrekt, Titel-Initial-Akzent greift. **0 Zahl-Paritäts-Abweichungen.**
- **Keywords: Übersetzung korrekt** — ABER macht ein **Quelldaten-Problem** sichtbar (siehe unten).
- **Der Übersetzer arbeitet regelkonform** (keine Typo-Korrektur, nichts erfunden). Was „falsch" aussieht,
  steht bereits **so in der DE/EN-Quelle**.

---

## ⚠️ Befund 1 — „sala de espera" = treue Übersetzung eines Quell-Müll-Keywords (KEIN Übersetzungsfehler)

Viele Keyword-Listen beginnen in der **DE-Quelle wörtlich mit „Wartezimmer"** (EN-Store: „waiting-room").
Beispiele aus dem Sample:

| uid | Motiv | DE-Quelle (Anfang) |
|----|-------|--------------------|
| 16 | BMW (freigestellt) | `Wartezimmer, abgase, achsen, alt, …` |
| 18 | BMW (freigestellt) | `Wartezimmer, bmw, abgase, achsen, alt, Makro, Macroaltes, …` |
| 23 | Baumgruppe Irland | `Wartezimmer, abenteuer, allein, …` |
|  2 | Altbau | `Wartezimmer alt, altbau, altes, …` |

→ ES „sala de espera" ist damit **korrekt**. Das Boilerplate ist ein **Indexierungs-Artefakt in der Quelle**.

**Prävalenz (gesamter Bestand, 8 907 Records):**
- `keywords` beginnt mit **`Wartezimmer`: 199 Records (2 %)**
- enthält **`blues`: 41** (uid 1 — steht so in DE+EN; vmtl. Tippfehler für „blau", aber nicht erfunden → erhalten)
- verschmolzene Token **`Macro<wort>` (z. B. `Macroaltes`): 17** (Quell-Korruption)

**Das ist eine Quelldaten-Entscheidung, keine ES-Frage** — sie betrifft DE/EN identisch und würde FR/RU genauso treffen.
Optionen:
- **(a) Quelle vor dem Vollauf säubern** (führendes `Wartezimmer`-Boilerplate aus den 199 DE-Records strippen,
  ggf. `blues`/`Macro…` reparieren) → sauberer für ALLE Sprachen, einmalig.
- **(b) So lassen** — fachlich harmlose SEO-Noise; Übersetzung bleibt treu.

Meine Empfehlung: **(a)**, single-field UPDATE auf DE-`keywords` der 199 (transaktional, Kollisions-/Backup-vorher),
**bevor** der ES-Vollauf läuft — dann ist es für TR/PL/IT/AR ebenfalls erledigt. Aber: dein Call, separat von B.

---

## Befund 2 — Keyword-Zeilen-Contract: `count mismatch … retrying` (selbstgeheilt)

Bei langen Keyword-Listen lieferte das Modell gelegentlich mehr Zeilen als Inputzeilen
(Reflow an Kommas). Der Command hat das erkannt und **per Einzel-Retry korrekt geheilt** —
Endstand `[DRY-RUN] Would write 100`. Funktioniert, kostet aber Extra-API-Calls.
Kein Blocker; falls gewünscht, kann ich den KW-Prompt-Contract noch härten.

## Befund 3 — Synonym-Varianz (akzeptabel für SEO-Keywords)

`macro` vs `macrofotografía`, `solo`/`soltero`/`solitario` (allein/alleinstehend) variieren zwischen
Records. Für Keyword-SEO unkritisch; keine Aktion nötig.

---

## Empfehlung

Übersetzungsqualität für **title + keywords ist freigabereif**. Vor dem Vollauf nur die
**Quelldaten-Frage (Befund 1)** klären. Danach: `--language=es --fields=title,keywords` ohne `--limit`,
Haiku, MD5-inkrementell.
