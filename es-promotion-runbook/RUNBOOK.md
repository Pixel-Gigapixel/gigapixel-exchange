# ES-Promotion nach gmbh (LIVE) — EINE Vorlage, ein Review

Vorbedingungen ✓ (read-only verifiziert): DE-uids biz==gmbh (Identity) · gmbh lang4=0 (sauber) ·
sys_file_reference→lang4 = 0 (ES erbt Bilder vom DE-Parent) · Slug-Fixes+term-073-Titel im biz-DB-Stand.

## SCHRITT 2 — Content (unsichtbar, /es/ bleibt 404)
Scoped-Copy der lang4-Schicht biz→gmbh, uid-gestrippt, transaktional, Idempotenz-Guard, per-Tabelle-Verify.
DRY-RUN (kein Write) lief grün: 107/232/55/7.

    python3 tools/promote_es_dump.py --target gmbh --dry-run   # Kontrolle (kein Write)
    python3 tools/promote_es_dump.py --target gmbh             # WRITE (transaktional)

Erwartete Verify-Counts (== biz):
    pages        lang4 = 107
    tt_content   lang4 = 232   (inkl. die 2 Plugin-list-Elemente 391/392)
    term         lang4 = 55
    category     lang4 = 7
KEIN cache:flush hier (Content ist unsichtbar bis Routing).

## SCHRITT 3 — Routing-Flip (Layer-1) → /es/ geht LIVE, fertig bestückt
Selektiver scp der 7 committeten Layer-1-Dateien (alle ES-additiv bzw. host-agnostisch, biz-bewährt):

    SRC=/mnt/raid1/gigapixel ; G=gigapx@dedi1178.your-server.de ; D=/usr/www/users/gigapx/deploy/app
    L1=(
      config/sites/main/config.yaml                                                   # +ES(4)-Sprachblock = DER Flip
      packages/dg_theme/Configuration/TypoScript/Setup/Lib/LanguageMenu.typoscript    # +ES im Switcher
      packages/dg_theme/Configuration/TypoScript/Setup/Plugin/plugin.tx_cart.typoscript
      packages/dg_theme/Configuration/TypoScript/Setup/Plugin/plugin.tx_cart_countries.typoscript
      packages/dg_theme/Classes/UserFunc/PageTitleUserFunc.php                        # generische SiteLanguage (biz-bewährt)
      packages/dg_theme/Configuration/TypoScript/Setup/Page/Page.typoscript           # siteLogo en,fr,ru,es
      packages/dg_theme/Resources/Public/Images/Logo/logo-es.svg                      # NEU
    )
    for f in "${L1[@]}"; do scp -P 222 "$SRC/$f" "$G:$D/$f"; done
    ssh -p 222 "$G" "cd $D && rm -rf var/cache/code/fluid_template/* && php82.bin.cli -d memory_limit=512M vendor/bin/typo3 cache:flush"

## GO-Struktur (Empfehlung)
EIN Review (dieses Runbook). EIN „GO Schritt 2+3" mit Auto-Gate:
  CC führt Schritt 2 aus → NUR wenn Verify == 107/232/55/7 (exakt) → CC führt Schritt 3 (Flip) aus.
  Bei JEDEM ✗ → STOPP vor dem Flip, kein Routing. (Served-Check von /es/ ist erst nach dem Flip möglich,
  weil /es/ bis dahin 404 ist → der Count-Verify IST der einzig mögliche Pre-Flip-Check, daher als harter Gate automatisiert.)
Danach: dein voller Served-Check /es/ (Blog/Info/Tier-1/Glossar/Form/Visual-Search/Schema) + FR/RU/DE-Regression + Nicht-Spanisch-Scan.
