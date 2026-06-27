# Cart-UI ES (212 Strings) — Review · KEIN Deploy

Pipeline: translate_fields + Guide (augmentiert: Platzhalter/HTML byte-genau, usted). Quelle DE (de.locallang.cart.xlf).
11 schon-approvte Keys gepinnt (Daniels Invoice/Mail-Wortlaut). 201 übersetzt.

## Ergebnis
- **212 übersetzt · 0 Check-Findings** (Platzhalter-Multiset · Zahlen · HTML-Tag-Skelett alle ✓)
- **15 geflaggt** (flagged.json): %s/%1$s/%2$s/%% + 3 HTML-`<a href="%1$s" target="%2$s">`-Consent-Strings — alle Platzhalter/Tags erhalten
- review-all.json: alle 212 (id · de · en · fr · es · pinned · checks)

## Bitte besonders prüfen (Terminologie/Recht)
- `tx_cart.submit_order`: „Kostenpflichtig bestellen" → **„Realizar pedido de pago"** — der gesetzliche Pay-Button.
  Üblicher: „Pedido con obligación de pago" o. ä. — dein Call.
- USt-Term: hier **„Impuesto sobre el valor añadido (%s)"** vs. CartPdf nutzt **„IVA 19 %"** → ggf. auf „IVA (%s)" vereinheitlichen.
- 3 Consent-Links (AGB/Widerruf/Datenschutz): „condiciones generales de contratación" / „instrucción de desistimiento" /
  „política de privacidad" — rechtliche Wortwahl gegenlesen.

## Danach
Dein Review (Stichprobe Fließtext + ALLE 15 geflaggten) → GO/Korrekturen → ich baue es.locallang.cart.xlf VOLL
(212, ersetzt das partielle 11er) → deploy → Checkout-Served-Check /es/.
