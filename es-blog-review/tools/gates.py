#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gates.py — Kanonischer Validator für den mehrsprachigen TYPO3-Rollout (gigapixel).
EINMAL geschrieben, jede Sprache/jeden Batch wiederverwendbar. Ersetzt die pro-Batch
neu gebauten build_*_es.py-Validatoren.

Aufruf:
    python gates.py <DE_payload.json> <ZIEL_payload.json>
    python gates.py de.json es.json --taglines 429,455   # Elemente mit übersetzbaren „…"-Claims

Payload-Format (beide Dateien): Array von Objekten mit mind. de_uid + bodytext.
Die Zieldatei trägt zusätzlich ru_uid/sorting/CType/header/subheader/bodytext.

Exit-Code 0 = alle Gates grün; 1 = mindestens ein FAIL (WARN bricht nicht ab).
"""
import json, re, sys, html, argparse
from collections import Counter

# --- Tag-Skelett ---------------------------------------------------------
def tag_seq(s):
    return [re.sub(r'\s+', ' ', t).strip() for t in re.findall(r'<[^>]+>', s or '')]

# --- Zahlen-Multiset (alle Zifferngruppen, inkl. Style-Attribute) --------
def nums(s):
    return Counter(re.findall(r'\d+', s or ''))

# --- Symbol-Multiset (Pfeile/Häkchen/Marken) -----------------------------
SYMBOLS = '↑↓→←↗↘✓✗✘⚠★☆§®™°±'
def syms(s):
    return Counter(c for c in (s or '') if c in SYMBOLS)

# --- &-Entities ----------------------------------------------------------
def amp(s):
    return (s or '').count('&amp;')

# --- Währungs-Token-Multiset (fängt auch Trennzeichen-Format) ------------
#   $3,000  $3.000  $2.000+  3.000 USD  2.000 EUR  £1,500 …  byte-genau vergleichen
# Symbol(+Betrag) ODER Betrag(+Symbol/ISO) — Betrag faengt UND endet auf einer Ziffer, also wird
# NACHGESTELLTE Interpunktion (. , ; :) NICHT mitgefangen (kein "€,"/"€."-Artefakt). Echte Mismatches
# (90 € vs 90 $, $3,000 vs $3.000) bleiben unterscheidbar.
CUR = re.compile(r'([$€£¥])\s?(\d[\d.,]*\d|\d)'                 # €90 / $3,000
                 r'|(\d[\d.,]*\d|\d)\s?([$€£¥])'                # 90 € / 2.100 $
                 r'|\b(\d[\d.,]*\d|\d)\s?(USD|EUR|GBP|CHF)\b')  # 90 EUR
def curr(s):
    out = []
    for m in CUR.finditer(s or ''):
        if m.group(1):   out.append(m.group(1) + m.group(2))        # Symbol vor Betrag
        elif m.group(4): out.append(m.group(3) + m.group(4))        # Betrag vor Symbol
        else:            out.append(m.group(5) + ' ' + m.group(6))  # Betrag + ISO
    return Counter(out)

# --- Deutsche Funktionswörter (NUR eindeutige; mit EN/ES kollidierende
#     Tokens wie in/an/am/so/war/man/die/see sind BEWUSST ausgeschlossen,
#     damit englische Titel à la „Stories in the Rock" nichts auslösen.
#     Echte DE-Prosa enthält praktisch immer der/das/und/ist/… ) ----------
GER = set("""
der das und oder ist sind wird werden wurde wurden nicht auch aber sich mit von fuer für
auf durch ueber über zwischen dass daß kann koennen können muss müssen soll sollen haben
hatte diese dieser dieses welche welcher welches ihre ihrer seine unsere damit weil denn
sowie beim vom zum zur dem des ein eine einen einem einer eines schon sehr mehr noch nur
gegen gegenueber gegenüber ohne nach bei aus dabei dazu hierfür wenn wodurch womit dadurch
unser unseren unserem unserer deutlich bereits jedoch sondern weshalb wodurch
""".split())

# häufige ASCII-Umlaut-Altlasten der DE-Quelle (zählen NICHT als Fehler in der DE-Seite,
# dürfen aber in der Zielsprache NICHT auftauchen) -> wir prüfen nur die Zielseite,
# daher als DE-Marker mitgeführt:
GER |= set("""
haeufige kuerze staedte raeume baeumen wohnraeumen konferenzraeume massnahmen wandfuellende
mindestaufloesung bildaufloesung produktivitaet buerogestaltung erfuellen loesen ermoeglicht
ermoeglichen ueberzeugendes gegenueber schlafqualitaet heilungsfoerdernd gaeste foerdern
""".split())

WORD = re.compile(r"[A-Za-zÀ-ÿ]+")

def _strip_citations(t):
    # „ … "  bzw.  „ … "  (Schließzeichen U+0022 / U+201C / U+201D)
    t = re.sub(r'„.*?[“”"]', ' ', t, flags=re.S)
    t = re.sub(r'"[^"]*"', ' ', t)            # gerade Anführungszeichen "…"
    return t

def german(s, strip_quotes=True):
    t = re.sub(r'<[^>]+>', ' ', s or '')
    if strip_quotes:
        t = _strip_citations(t)
    t = html.unescape(t)
    found = [w for w in WORD.findall(t.lower()) if w in GER]
    found += re.findall(r'\bKI\b', t)        # KI (Künstliche Intelligenz) bleibt in JEDER Zielsprache Deutsch -> Residue
    return found

# --- Hauptlauf -----------------------------------------------------------
def run(de_path, tgt_path, tagline_uids):
    DE = {e['de_uid']: e for e in json.load(open(de_path, encoding='utf-8'))}
    TG = {e['de_uid']: e for e in json.load(open(tgt_path, encoding='utf-8'))}
    missing = set(DE) ^ set(TG)
    if missing:
        print("FEHLER: de_uid-Mengen unterschiedlich:", sorted(missing)); return 1

    cols = ("uid","G1tag","G2num","Gsym","G&","Gcur","G3-de")
    print("%-6s %-6s %-6s %-6s %-6s %-6s %s" % cols)
    print("-"*62)
    fail = False
    warns = []
    for uid in sorted(DE):
        d, t = DE[uid]['bodytext'], TG[uid]['bodytext']
        g1 = tag_seq(d) == tag_seq(t)
        g2 = nums(d) == nums(t)
        gs = syms(d) == syms(t)
        ga = amp(d) == amp(t)
        gc = curr(d) == curr(t)
        prose_de = german(t, strip_quotes=True)        # FAIL: DE in echter Prosa
        inquote_de = [w for w in german(t, strip_quotes=False) if w not in prose_de]
        g3 = (len(prose_de) == 0)
        row_fail = not (g1 and g2 and gs and ga and gc and g3)
        fail |= row_fail
        mark = lambda b: "ok" if b else "FAIL"
        print("%-6s %-6s %-6s %-6s %-6s %-6s %s" % (
            uid, mark(g1), mark(g2), mark(gs), mark(ga), mark(gc),
            "ok" if g3 else "FAIL"+str(dict(Counter(prose_de)))))
        if not g1:
            for i,(a,b) in enumerate(zip(tag_seq(d), tag_seq(t))):
                if a != b: print("        ! Tag #%d  DE %r | ZIEL %r" % (i,a,b)); break
            print("        ! Tag-Anzahl DE=%d ZIEL=%d" % (len(tag_seq(d)), len(tag_seq(t))))
        if not g2: print("        ! Zahlen DE-only=%s ZIEL-only=%s" % (dict(nums(d)-nums(t)), dict(nums(t)-nums(d))))
        if not gs: print("        ! Symbole DE=%s ZIEL=%s" % (dict(syms(d)), dict(syms(t))))
        if not gc: print("        ! Währung DE=%s ZIEL=%s" % (dict(curr(d)), dict(curr(t))))
        # „…"-DE: entweder absichtliches Fremdzitat (ok) ODER nicht-übersetzter Claim (Problem)
        if inquote_de:
            kind = "Claim NICHT uebersetzt?" if uid in tagline_uids else "Fremdzitat? (verifizieren)"
            warns.append('  WARN uid %s: DE-Tokens in Anfuehrung: %s  -> %s' % (uid, dict(Counter(inquote_de)), kind))

    print("-"*62)
    for w in warns: print(w)
    if tagline_uids:
        for uid in tagline_uids:
            extra = german(TG[uid]['bodytext'], strip_quotes=False)
            tag = "OK (Claim spanisch)" if not extra else ("PRÜFEN: "+str(dict(Counter(extra))))
            print("  Tagline-Check uid %s: %s" % (uid, tag))
    print("\n%s" % (">>> ALLE GATES GRÜN <<<" if not fail else ">>> FAIL — siehe oben <<<"))
    return 1 if fail else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("de_payload"); ap.add_argument("target_payload")
    ap.add_argument("--taglines", default="", help="kommagetrennte de_uids mit übersetzbaren „…\"-Claims")
    a = ap.parse_args()
    tl = {int(x) for x in a.taglines.split(",") if x.strip()}
    sys.exit(run(a.de_payload, a.target_payload, tl))
