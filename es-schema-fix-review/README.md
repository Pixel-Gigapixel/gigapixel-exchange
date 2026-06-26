# Schema-GEO-Fix (SchemaOrgViewHelper + Controller + Templates + XLIFF) — Review · KEIN Deploy

## Was der Diff macht (8 Dateien, PHP-lint sauber, XML valid)
1. **SchemaOrgViewHelper.php**: neue Args `baseUrl` + `jobTitle` (mit DE-Fallback-Defaults → kein Regress,
   wenn ein Template sie nicht übergibt). `url = baseUrl/slug`, `inDefinedTermSet.@id = baseUrl`,
   `inDefinedTermSet.name = setName` (statt hartdeutsch 'Gigapixel-Glossar'), `author.jobTitle = jobTitle`.
2. **TermController** (list+show) & **MethodologyController**: `match($languageId)` um **Fall 4 (ES → '/glosario')**
   ergänzt (war Lücke → ES fiel auf '/glossar' = deutsch); `schemaBase = https://gigapixel.gmbh<langBase><slug>`
   assigned. Behebt zugleich ES-Breadcrumb-URL + sichtbare Methodik-Links (/es/glosario statt /es/glossar).
3. **Templates** List/Show/Index: reichen `baseUrl="{schemaBase}"` + `jobTitle`/`setName` (f:translate) durch.
4. **locallang.xlf** (source): neuer Key `schema.author_jobtitle` (= DE-Original).
5. **es.locallang.xlf** (NEU): `schema.glossary_set_name=Glosario Gigapixel`, `schema.methodology_set_name=
   Metodología Gigapixel`, `schema.author_jobtitle=…` (ES). de/fr/ru fallen auf Source zurück (kein Regress).

## Parität
Der url/@id-Fix wirkt auf ALLE Sprachen (jede nutzt ihren langBase+slug). name/jobTitle über XLIFF lokalisierbar.

## ⚠️ Zwei Punkte für dich
- **ES-Reviewbedarf (Rechtsterm + Methodik-Name):**
  - `schema.author_jobtitle` ES = „Perito judicial designado y jurado para imágenes gigapíxel" — **Entwurf**,
    bitte den genauen Rechtstitel bestätigen/korrigieren.
  - `schema.methodology_set_name` ES = „Metodología Gigapixel" — Entwurf.
- **Breiterer ES-Chrome-Gap (NICHT in diesem Diff):** Die ext hat **kein vollständiges es.locallang.xlf** →
  auf /es/glosario fallen ~16 Template-Labels (CTA, „Related Terms", „Category:", Breadcrumb) auf die
  EN-Source zurück; und der Controller-`match()` für `<title>`/Description hat **keinen Fall 4** → ES-Titel/Desc
  fallen auf DEUTSCH. Eigener Folge-Schritt (du lieferst die ~16 ES-Labels + ich ergänze match-Fall 4),
  analog XLIFF/Form. Sichtbar in deinem Served-Check.

## Flow
Diff reviewen → GO → ich deploye (8 Dateien rsync + cache:flush) → du verifizierst ES-Schema served
(/es/glosario/-Pfade, „Glosario Gigapixel", 0 hartdeutsch im DefinedTermSet).
