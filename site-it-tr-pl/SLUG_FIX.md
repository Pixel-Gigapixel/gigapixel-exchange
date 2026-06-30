# Regress-Fix B — Katalog-PDP-Struktur-Slug zurück auf "details" (IT/TR/PL)

## Schritt 0 — Slug-Diff (Struktur-/Eltern-Seiten, IT/TR/PL ≠ DE)
EINZIGER gebrochener Struktur-Slug = **pid 19** (PDP-Routing-Eltern, doktype 189, DE `/details`):
| Sprache | vorher (gebrochen) |
|---|---|
| IT | /acquistare-foto-gigapixel |
| TR | /gigapixel-fotograf-sat-n-al |
| PL | /kup-zdjecie-gigapikselowe |
Gegengeprüft, NICHT betroffen: /blog (pid 142, in allen Sprachen `/blog`, 55 Posts hängen sicher),
Produkt-Storage (pid 17, Sysfolder, kein Sprach-Overlay). Content-Slugs (glossario/privacy/metodologia…)
bleiben bewusst lokalisiert. → kein weiterer Struktur-Slug gebrochen.

## Fix — biz UND gmbh, je transaktional, Backup
pid-19-Overlays IT/TR/PL slug → `/details` (Backup: ~/exports/site-rollout/pid19_slug_backup.json).
biz: uid 803/884/722 · gmbh: uid 827/934/720 → alle NACHHER `/details`, keine Kollision.

## Härtung
- `rollout.py:page_slug_for()` (greift in ensure_page_overlay + --from-review): Struktur-/Routing-Seiten
  (doktype != 1) + Siteroot (`/`) ERBEN den DE-Slug; nur Content-Seiten (doktype 1) werden lokalisiert.
- RUNBOOK_NEXT_LANGUAGE.md Addendum: "Struktur-/PDP-Slugs nicht übersetzen" + "nach jeder Promotion eine
  Katalog-PDP served-checken".

## Verify (Schritt 7+8) — served, nach Flush (biz+gmbh) + Sitemap-Regen
gmbh: /it/details/<p> /tr/details/<p> /pl/details/<p> = 200 (lang korrekt) · /es/details/<p> + /details/<p> = 200 (kein Kollateral).
biz (temp-Auth): dieselben 5 = 200. Alte URL /it/acquistare-foto-gigapixel/<p> = 404 (korrekt weg).
PDP-Canonical: kein explizites canonical (bestehendes Design, ES identisch) — hreflang-Selbstreferenz zeigt
korrekt auf /it/details/<p>; Related-Link /it/details/hauptgebaeude-… = 200.
Sitemap regeneriert (200); IT-Produkt-Sitemap enthält /it/details/-URLs (z.B. /it/details/lake-tekapo-2).
Testprodukt: schloss-belvedere-bei-weimar.
