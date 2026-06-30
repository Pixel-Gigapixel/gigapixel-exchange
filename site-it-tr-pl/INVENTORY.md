# Inventar-Abgleich (biz, deleted=0) — IT/TR/PL vs. Referenz

Referenz = Inventar des Workstreams (ES langId4 = Vorlage): pages 107, tt_content 232, Glossar 55+7, XLIFF 361.

## pages-Overlays

| Sprache | Ist | Ref (ES) | Gap | Kommentar |
|---|---|---|---|---|
| TR (5) | 107 | 107 | **0** | vollständig |
| PL (6) | 107 | 107 | **0** | pid 371 mit glm-5.2 grün → inserted |
| IT (7) | 107 | 107 | **0** | pid 138 + 371 mit glm-5.2 grün → inserted |

**Gap = 0 für alle drei Sprachen.** Die zuvor 3 DE-Fallback-Seiten (IT 138/371, PL 371) wurden mit
**glm-5.2:cloud** gate-grün übersetzt (DE_HI/EN_HI/ES_HI=0, Zahl/Tag/&-Parität) und auf biz inserted
(Page+Content-Overlay neu, da vorher keins existierte).

Davon je Sprache **17 Struktur-Overlays** (Shortcuts doktype 4, Plugins 190, externe 3) — neu angelegt
(`structural_overlay.py`), Titel via glm übersetzt, Slug/doktype/shortcut/url von DE gespiegelt. Diese
hatte der Content-Rollout zuvor übersprungen (kein tt_content) → schloss die ES-Parität.

## tt_content-Overlays

| Sprache | Ist | Ref (ES) | Kommentar |
|---|---|---|---|
| IT | 235 | 232 | ≥ ES — alle DE-Quell-Elemente abgedeckt (inkl. reparierter + gate_fail-Recovery) |
| TR | 237 | 232 | ≥ ES |
| PL | 236 | 232 | ≥ ES |

(Differenz zu ES kommt aus zusätzlich abgedeckten Elementen + Plugin-Overlays; soft-deletete
Spanisch-Altstände zählen nicht mit.)

## Glossar

| | IT | TR | PL | DE |
|---|---|---|---|---|
| Terme | 55 | 55 | 55 | 55 |
| Kategorien | 7 | 7 | 7 | 7 |

Plugin-Elemente (819/820 auf pid 391/392) waren bereits vom Site-Rollout als tt_content-Overlay angelegt
→ `glossar_load.py` legt für lang 5/6/7 NUR Terme + Kategorien an (kein Doppel-Insert).

## XLIFF

Je Sprache 361 trans-units in 6 Dateien (cart_gigapixels/locallang 45, dg_theme/CartPdf 27, Form 20,
locallang.cart 212, gigapixel_glossary/locallang 19, gigapixels_visualsearch/locallang 38) — **Gap 0**.
Deployed nach biz (rsync) + cache:flush. Quelle = `<source>` (en/de) → Zielsprache; Whitespace/Platzhalter
(`%s`, `→`, Entities) byte-genau erhalten.

## meta-keywords

`page.meta.keywords` zieht via TypoScript `override.field = keywords` aus dem pages-Feld `keywords`
(in PAGE_TRANSLATE) → wurde beim Page-Lauf je Sprache übersetzt. Nicht-leer: IT 19 / TR 19 / PL 17
(DE-Referenz: 19 keyword-tragende Seiten). Kein separates Tooling nötig.

## Gate (konsolidiert, je Sprache)

| | DE_HI | EN_HI | ES_HI | Verdikt |
|---|---|---|---|---|
| IT | 0 | 0 | 0 | PASS |
| TR | 0 | 0 | 0 | PASS |
| PL | 0 | 0 | 0 | PASS |

Definition: GRÜN ⇔ DE_HI=0 & EN_HI=0 & ES_HI=0 (HIGH-Token-Sets in `site_gate.py`, kanonisch an
`catalog_sample_gate.py` ausgerichtet, + neuer ES_HI-Tier). Bewahrte Bibliografie/Zitate/URLs/Produktnamen
werden vor dem Scan entfernt (siehe `gate/postrun_*.txt`, inkl. transparenter Zitat-Review-Liste).

**Netto-Gap: 0.** Alle inserted Site-Overlays in Zielsprache, gate-grün (DE_HI=0 & EN_HI=0 & ES_HI=0).
Legal-Seiten verifiziert: Datenschutz (pid 49) IT „Informativa sulla privacy" / TR „Gizlilik Politikası" /
PL „Polityka prywatności"; Impressum (pid 11) IT „Fornitore del servizio" / TR „Hizmet Sağlayıcı" /
PL „Usługodawca" (DE-Firmenadresse korrekt bewahrt).
