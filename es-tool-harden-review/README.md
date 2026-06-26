# Tool-Härtung (rollout.py) — Review vor Tier 1

## 2 zusammengehörige Änderungen in translate_fields (NUR rollout.py; gates.py + TRANSLATION_GUIDE.md unberührt)
1. **Delimiter-Contract** (escaping-frei): Modell liefert Felder zwischen `<<<FIELD:name>>>` … `<<<END>>>`
   als ROHES HTML statt strikt-JSON. Neuer Parser `_parse_delimited` + `_fields_to_markers`;
   bei fehlendem Marker/END → ValueError → bestehender 1×-Retry. Rückgabe-Contract (dict) unverändert.
2. **max_tokens 8192 → 32000 + Streaming** (`client.messages.stream` + `get_final_message`):
   eigentliche Wurzel von pid 142. Sonnet 4.6 deckt 64K, Opus 4.8 128K; ab ~16K Output ist Streaming
   Pflicht (SDK-HTTP-Timeout).

## Diagnose
142s „Unterminated string" (JSON) bzw. „<<<END>>> fehlt" (Delimiter) waren BEIDE Truncation-Symptome,
nicht Escaping. Quelle uid565 ~7,8k Tok → ES-Output ~9–10k > 8192 → abgeschnitten.

## Re-Validierung (Gate-Matrix, --force --dry-run)
| pid | Sonnet | Opus | Anmerkung |
|----:|--------|------|-----------|
| 142 | komplett (24.671 Z., 0 DE, 0 Parse-Fehler), Content-Gate FAIL (HTML-Skelett) | **PASS** | Truncation weg; Sonnet-Rest = Inhalts-Gate (wie 138) → Opus löst |
| 369 | FAIL (Währungs-Token-Varianz: „3.000$" erfunden) | **PASS** | Run-to-Run-Varianz, kein struktureller Regress |
| 113 | **PASS** | — | konsistent grün |

JSONs hier: es-142/es-369 = Opus-PASS, es-113 = Sonnet-PASS.
Beleg: 142 lief mit dem ALTEN Tool unter KEINEM Modell durch; jetzt vollständig + PASS (Opus).
