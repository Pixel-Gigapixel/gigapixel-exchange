# Form 46 (Kontakt) — ES-Lokalisierung zur Übersetzung

## Mechanik
- Plugin uid 180 (pid 46) = form_formframework, persistenceIdentifier = EXT:dg_theme/.../Forms/kontakt.form.yaml
- Labels über Form-Framework-translationFiles (renderingOptions.translation.translationFiles → Form.xlf)
- Form.xlf = DE-Source (20 trans-units), fr.Form.xlf / ru.Form.xlf = je 20 targets
- **es.Form.xlf fehlt** → /es/contacto Formular zeigt DE-Labels (gleiche Lücke wie Visual-Search-XLIFF)
- TYPO3 löst es.Form.xlf per Sprachkonvention automatisch auf (kein YAML-Edit nötig)

## Zu übersetzen (20 Strings, Keys = kontakt.element.<id>.properties.<label|placeholder|options.*> u.a.)
Feld-Labels (Name/E-Mail/Firma/Telefon/Nachricht) + Placeholders + Kontaktoptionen (2 Radio) +
Seiten-Labels (Kontakt/Zusammenfassung) + Buttons (Senden/Zurück/Weiter) + Bestätigung
(„Ihre Nachricht wurde versendet.").

→ Du verfasst die 20 ES-target (wie die Visual-Search-XLIFF, FR als Vorbild), ich baue es.Form.xlf
(Mirror von fr.Form.xlf, target-language="es") → Deploy → served-Check /es/contacto Formular spanisch.
