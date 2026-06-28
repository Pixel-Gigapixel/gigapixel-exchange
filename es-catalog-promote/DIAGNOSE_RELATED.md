# Related-Sektion „deutsch auf ES" — Trace (READ-ONLY): KEIN langCode-Bug

## Empirie (live gmbh, post-flush, /es/details/orion-nebula)
- H1 „Nebulosa de Orión" ✓ · Related-Heading **„Imágenes relacionadas"** ✓ · 2/3 Related-alts spanisch
  („El Gran Ahornboden cerca de Karwendel…", „Camino de hormigas…").
- 1/3 deutsch: **„Schloss Belvedere bei Weimar"** — weil dessen es-title **leer** ist → `displayTitle`
  fällt auf die DE-`title` zurück. **uid 2: es='' UND fr='' UND ru=''** → auf ALLEN Sprachen DE (auch FR).

## Befund: kein 5. langCode-Spot
- `RelatedGigapixel.html` rendert `alt="{cartgigapixels:displayTitle}}"` → derselbe (bereits gefixte) VH; `4=>'es'` ist auf gmbh deployed.
- `TranslationRepository::get` = per-Request-static (frisch aus Live-DB), kein Stale-Cache.
- Die deutschen Related-Items sind **leere es-Titel** (Fallback auf DE), kein Auflösungs-Bug.

## Die eigentliche Lücke: leere ES-Titel
- es-title leer gesamt: **2.376** → davon **2.318 auch in FR leer** (reine Eigennamen, bewusst überall unübersetzt — z. B. „Schloss Belvedere bei Weimar").
- **58** = „ES leer ABER FR vorhanden" — der echte „ES zeigt DE, FR zeigt Französisch"-Gap.
  Beispiele: „Der Turm des Intershops in Jena" (FR „La tour du Intershop à Jena"), „Der Berliner Hauptbahnhof
  an der Spree", „Brandenburger Tor mit Vorplatz" — **deskriptive** Titel mit **EN-Store leer**.
  → Das ist die EMPTY-Regel-Über-Leerung wie die ursprünglichen 353, aber der **EN-leere** Teil, den der
  damalige Fix (keyed auf EN-Präsenz) übersprang. Die verfeinerte Regel 4 (deskriptives DE-Wort → übersetzen) trifft sie.

## Vorschlag (DB-Job, KEIN Template-Change — dein GO)
1. **biz:** die 58 es-title-Rows löschen → `gigapixels:translate --language=es --fields=title` (MD5 zieht nur die 58)
   → Verify: 58 jetzt nicht-leer (Re-Gate: empty-es-mit-FR = 0).
2. **gmbh:** die 58 es-title-Rows aus den biz-Werten gezielt updaten (wie Dims-Fix Schritt 5, per source_uid).
3. uid-Liste: `empty_es_title_fr_present_uids.json`.

> Read-only. Kein Write bis zu deinem GO. Die 2.318 (auch-FR-leer) bleiben bewusst leer (Eigennamen) — separate Entscheidung, falls überhaupt.
