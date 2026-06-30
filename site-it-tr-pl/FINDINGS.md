# FINDINGS — Spanisch-Leak im Site-Content (Root Cause + Repair)

## Symptom
tt_content-Overlays, die als TR/PL/IT markiert waren (`sys_language_uid` 5/6/7), enthielten **spanischen**
Text — z. B. die IT-Datenschutzseite („Política de privacidad …"), die TR-Homepage-Sektion
(„Imágenes que convencen …"), Tier-2-Landingpages und Blog-Absätze. pages-Felder (title/keywords/
description) waren korrekt — nur der Seiten-**Content** war betroffen.

## Root Cause
`rollout.py` Zeile 555 (`humanize_gate_feedback`) erzeugte das Gate-Retry-Feedback hartkodiert mit:

> „[uid X] Diese Sätze sind noch DEUTSCH — übersetze sie vollständig **ins Spanische**: …"

Ablauf: Pass-1-Übersetzung hat oft etwas deutschen Rest → Gate G3-de schlägt an → Retry-Feedback sagt
„ins Spanische" → Modell übersetzt das ganze Feld ins Spanische → Pass-2-Gate grün (Spanisch hat keine
DE-/EN-Tokens, korrekte Zahlen/Tags) → **Commit von spanischem Content**.

Das betraf **beide** Läufe: den ursprünglichen Sonnet-Site-Lauf UND den ersten glm-Lauf. Verstärkt durch
`TRANSLATION_GUIDE.md`, das durchgängig **spanische** Beispiele nutzt (historischer ES-Rollout) — glm
ahmt bei langem Content die Beispielsprache nach und driftet ins Spanische.

Der vorhandene Zwei-Tier-Gate (DE_HI/EN_HI) konnte das **prinzipiell nicht** fangen: Spanisch ist weder
Deutsch noch Englisch.

## Umfang (vor Repair, robuster ES-Detektor)
- TR: ~56 Elemente / 28 pages
- IT: ~73 Elemente / 32 pages
- PL: ~77 Elemente / 27 pages

## Fixes
1. **Root Cause:** `humanize_gate_feedback(gout, de, es, lang)` — Feedback nennt jetzt die echte
   Zielsprache (`LANG_NAME[lang]`); Callsite reicht `lang` durch.
2. **Prompt-Härtung:** `translate_fields` setzt einen ZIELSPRACHEN-ANKER an den Anfang des System-Prompts
   („Übersetze AUSSCHLIESSLICH ins <Ziel>; die spanischen Beispiele unten illustrieren nur REGELN, sind
   NICHT die Zielsprache; gib niemals Spanisch aus, außer Ziel ist Spanisch.") + Verstärkung im User-Intro.
3. **Gate-Erweiterung:** neuer **ES_HI-Tier** in `site_gate.py` — erkennt diese Fehlerklasse künftig.
   FP-sicher kuratiert: kurze Tokens `el/los/las/para/por/…` BEWUSST raus (echte TR-Wörter „el"=Hand,
   „para"=Geld; PL „las"=Wald). Marker = akzentuierte/eindeutige ES-Wörter (resolución, imágenes,
   megapíxeles, fotografía, …). Produktnamen („Adobe Super Resolution") + Bibliografie/Zitate/URLs werden
   vor dem Scan entfernt.
4. **Repair (zwei Runden):**
   - Dry-Run `rollout.py --force` (gefixtes Feedback + gehärteter Prompt) → JSON.
   - `repair_es_leak.py`: gate-PASS-Seiten → alte Overlays soft-delete → `--from-review` insert.
   - `force_commit_clean.py`: Seiten, die nur an einem gates.py-False-Positive (G3-de auf „bei" o. ä.)
     scheiterten, aber unabhängig verifiziert sauber sind (site_gate sauber + Zahl-/&-Parität DE↔neu),
     werden force-committed. Toleranz `--max-es/--max-en` für echte TR/PL-Wörter, die wie ES/EN aussehen.

## Ergebnis
**ES_HI = 0** in IT, TR, PL (Postrun-Gate, `gate/postrun_*.txt`). Verifiziert auch im **served HTML**
aller 12 gerenderten Seiten (0 DE/EN/ES im sichtbaren Body).

Alte spanische Overlays sind soft-deleted (deleted=1) — reversibel, kein Datenverlust.

## Rev. 2 — glm-5.2 löst die 3 Reststeiten
Nach Umstellung des Übersetzungs-Modells auf **glm-5.2:cloud** (Z.ai-Flagship; `OLLAMA_MODEL` zentral in
`rollout.py`, alle Tools nutzen `R.OLLAMA_MODEL`; Dry-Run-Log `model=glm-5.2:cloud` verifiziert) wurden die
3 zuvor harten Seiten gate-grün übersetzt und auf biz inserted:
- IT pid 138 (uid 548, HTML-Tag-Skelett) → PASS
- IT pid 371 (uid 799, „24/7") → PASS (nach 1 Gate-Retry)
- PL pid 371 (uid 799, „KI"/Zahl) → PASS (nach 1 Gate-Retry)

Verifiziert ES_HI=0 + Sprachprobe (IT „Airport Lounge: immagini Gigapixel…", PL „Poczekalnie lotniskowe…").
**Keine DE-Fallback-Content-Seite mehr offen. Pages-Gap = 0 (107/107/107).**
