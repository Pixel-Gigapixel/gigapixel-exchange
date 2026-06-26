# ES-Chrome-Gap — zur Übersetzung (Glossar-Ext)

Zwei Quellen machen /es/glosario teils EN/DE trotz spanischer Term-Daten:

## A) XLIFF-Template-Labels ohne ES-Target (23 Keys)
es.locallang.xlf hat erst die 3 schema-Keys (Schema-Fix). Diese 23 brauchen ES-target (FR als Vorbild).
→ Du lieferst die ES, ich ergänze sie in es.locallang.xlf (Mirror von fr.locallang.xlf).

SICHTBARE CHROME (Priorität — das siehst du auf /es/glosario):
  glossary.title           EN 'Glossary'              FR 'Glossaire'
  glossary.hero_sub        EN 'The key terms …'       FR 'Les termes clés …'
  glossary.breadcrumb      EN 'Glossary'              FR 'Glossaire'
  methodology.title        EN 'Methodology'           FR 'Méthodologie'
  term.category_label      EN 'Category: '            FR 'Catégorie : '
  term.related_title       EN 'Related Terms'         FR 'Termes associés'
  term.expert_intro        EN 'Explained by'          FR 'Expliqué par'
  term.expert_role         EN 'Expert in gigapixel photography'  FR 'Expert en photographie gigapixel'
  cta.has_gallery          EN 'Find matching images …'           FR 'Trouvez des images …'
  cta.no_gallery_pre       EN 'Find images matching this topic via '  FR 'Trouvez des images … via '
  cta.no_gallery_link      EN 'visual search'         FR 'la recherche visuelle'
  cta.no_gallery_post      EN ' in the portal.'       FR ' dans le portail.'
  cta.gallery_license      EN 'You can license these motifs …'   FR 'Vous pouvez licencier …'
  cta.btn                  EN 'Browse all images →'   FR 'Explorer toutes les images →'
  gallery.heading.application  EN 'Suitable motifs for %s'  FR 'Motifs adaptés pour %s'   (Platzhalter %s behalten)
  gallery.heading.generic      EN 'Matching image motifs in the portal'  FR 'Motifs d'images correspondants …'

KATEGORIE-KEYS (7) — evtl. REDUNDANT: die DB-Kategorien sind bereits ES (Captura/Procesamiento/…).
Wenn das Template die DB-Titel rendert (nicht diese XLIFF-Keys), kannst du sie überspringen. Zur Sicherheit:
  category.aufnahme=Capture · verarbeitung=Processing · produktion=Production · druck=Print ·
  medien=Media · tech=Technology · anwendung=Application  (ES = Captura/Procesamiento/Producción/Impresión/Medios/Técnica/Aplicación)

## B) Controller <title>/Description — match() ohne Fall 4 (ES → fällt auf DEUTSCH)
Beide Controller haben `match($languageId)` mit 1/2/3/default, KEIN Fall 4. Ich füge Fall 4 mit deinen ES-Strings ein.
Du lieferst 4 Strings (je title + description):

TermController::listAction  (DE-default als Referenz):
  title: 'Gigapixel-Glossar – Fachbegriffe erklärt'
  desc:  'Die zentralen Fachbegriffe echter Gigapixel-Fotografie – verständlich erklärt, von der Aufnahme bis zur Verarbeitung.'
MethodologyController       (DE-default als Referenz):
  title: 'Methodik der Gigapixel-Fotografie – eigene Aufnahmeverfahren | Gigapixel GmbH'
  desc:  'Aufnahmeverfahren, Verarbeitungsschritte und Qualitätskriterien hinter echten Terapixel-Panoramen – transparent erklärt.'
(FR-Varianten stehen im Source/Code als weiteres Vorbild.)

## Danach
Du → ES-Labels (A) + 4 Strings (B) → ich: es.locallang.xlf erweitern + match-Fall 4 (2 Controller) →
Deploy → dein Served-Check: /es/glosario Labels spanisch + Tab-Titel/Meta spanisch. Letzter Chrome-Rest.
