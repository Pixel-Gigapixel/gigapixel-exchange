# ES-Invoice/Mail-Lokalisierung — Review

f157159 (EN/FR/RU-Invoice-Mechanismus) ist BEREITS auf gmbh live (diff=0). Der ES-Gap ist fehlende ES-Übersetzung.

## (A) Invoice-PDF — es.CartPdf.xlf  (PRIMÄR, 27 Strings)
CartPdf.xlf = Source (27 units) · fr.CartPdf.xlf = Vorbild (27 targets). Du verfasst 27 ES-target →
ich baue es.CartPdf.xlf. (Formelles Rechnungs-Spanisch/usted; Platzhalter/Beträge/ISO byte-exakt.)
Befund: Invoice-PDF zieht 30× CartPdf.xlf + 3× dg_theme-locallang.xlf + 3× tx_cart-Modell — KEIN locallang.cart.
→ kein Invoice-String fällt durch locallang.cart. ABER:

## (B) RESIDUAL (siehe RESIDUAL_KEYS.md)
- 3 dg_theme-locallang.xlf-Keys im Invoice-PDF (delivery_number / order_product.title / .count):
  es.locallang.xlf (dg_theme allgemein) FEHLT → fallen auf Source. 3 ES-Strings nötig.
- Bestell-/Download-MAIL nutzt tx_cart.mail.* aus locallang.cart.xlf (fr: 9 mail-Keys belegt):
  es.locallang.cart.xlf (Mail-Subset) für die spanische Käufer-Mail.

## (C) SEPARATE Scope-Frage (NICHT invoice/mail — du entscheidest)
fr/ru.locallang.cart.xlf haben je 212 Targets = die KOMPLETTE Cart-Checkout-UI (Schritte/Buttons/
Validierung). Davon sind die Länder bereits via tx_cart_countries.typoscript ES (Layer-1). Die restlichen
~200 Cart-UI-Strings auf /es/ (Checkout-Flow) sind ein eigener ES-Vollständigkeits-Punkt — heute schließen
oder als bekannten Folge-Punkt parken?
