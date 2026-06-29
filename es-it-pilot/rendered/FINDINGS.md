# biz /it/ — gerendertes HTML, Befund (CC, read-only Served-Check)

Quelle: `GET https://gigapixel.biz/it/details/schloss-belvedere-bei-weimar` (uid 2),
über temporären Wegwerf-Auth-User (danach revoked → 401 bestätigt). Volles HTML: `biz_it_details_schloss-belvedere.html`.

## KATALOG-RENDER-SPOTS = alle Italienisch ✓  (das, was dieser Deploy verdrahtet)

| Spot | Ergebnis |
|------|----------|
| HTTP | **200**, kein Fatal/Uncaught/Exception/**PhotographerName** (0×) — isolierte Dateien tragen das Feature nicht |
| `<html lang>` | `it-IT` ✓ |
| **H1** (DisplayTitle) | `Schloss Belvedere presso Weimar` ✓ (IT-Titel) |
| **Beschreibung** (Show.html) | `Il Castello Belvedere presso Weimar come ripresa gigapixel da 0,25 GP con 31064 x 8049 pixel di Daniel Richter. Adatto per decorazione murale…` ✓ |
| **Maße** | `31064 x 8049` ✓ (== format_width×height, keine Halluzination) |
| **og:title** | `Schloss Belvedere presso Weimar` ✓ |
| **og:description** | Il Castello Belvedere presso Weimar come ripresa gigapixel da 0,25 GP con 31064 x 8049 pixel di Daniel Richter. Adatto per decorazione murale rappresentativa, stampe di grande formato e allestimento f ✓ |
| **JSON-LD** (Schema) | `"@type":"Product"` → `"description":"Il Castello Belvedere presso Weimar…"` Italienisch ✓ |
| **DE-Residue-Phrasen** im Content | **0** (kein „als Aufnahme von / Echte Kameraaufnahme / Geeignet für …") |

## Noch Deutsch = die von dir SEPARAT zurückgestellten Schichten (NICHT diese Render-Spots)

| Stelle | Snippet | Schicht |
|--------|---------|---------|
| Footer/Nav-Menü | `/it/bilder-verkaufen`, „Bilder für Spanndecken & Wandgestaltung", „Bilder für Agenturen…" | **Seitenbaum-Übersetzung** (Schicht-1-Dump, langId-7 pages/tt_content — wie promote_es_dump für ES) — noch nicht gelaufen |
| Related-Heading | `<h2 class="gp-similar-title">Ähnliche Bilder` | UI-Label (XLIFF) |
| Claim-Block | „Alle Bilder besitzen eine Auflösung… Zoomen Sie auch in die Bilder…" | statischer Trust-Text (XLIFF/Template) |
| `<title>`-Suffix | „… - Gigapixel-Foto kaufen \| Gigapixel GmbH" | PageTitle-Suffix (A-Labels) |
| og:image:alt-Suffix | „… – Gigapixel-Foto" | Label |

→ Genau dein „A-Labels/Forms/Checkout + Seitencontent kommen separat". Die **Karten-/Produkt-Inhalte** (Titel, Beschreibung, Maße) sind Italienisch; nur **Section-Label + Seitenbaum-Menü** sind noch DE.

## Hinweis: `inLanguage` fehlt im JSON-LD
Nicht IT-spezifisch — auch das **live-akzeptierte ES**-Schema hat kein `inLanguage` (SchemaViewHelper emittiert es generell nicht). Kein Regress dieses Deploys; falls gewünscht, separater Schema-Zusatz.
