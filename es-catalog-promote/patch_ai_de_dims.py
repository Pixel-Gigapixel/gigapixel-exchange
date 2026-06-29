#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministischer, CHIRURGISCHER Patch der falschen Maße/GP in ai_description_de (biz).
KEINE Regenerierung — re.sub ersetzt NUR die Maß- und GP-Spans; alles andere bleibt byte-exakt.
Quelle der Wahrheit: format_width/format_height (== format_px == Zoomify-ImageProperties.xml, verifiziert).

Behandelt beide Korruptionsformen:
  - dims_wrong: "W × H Pixel/px" ≠ format_w×h        -> Maß ersetzen (Stil: Separator ×/x, Tausender, Einheit erhalten)
  - gp_wrong:   "X,XX Gigapixel/GP" ≠ W·H/1e9        -> GP-Figur ersetzen (Einheit/Spacing erhalten)

Sicherheit:
  - Match-Set-Guard: nur Records mit dims_wrong ODER gp_wrong (Re-Run idempotent: korrigierte fallen raus).
  - Validierung pro Record: aus dem NEUEN Text Maß+GP re-extrahieren -> MUSS == Truth; sonst SKIP+flag (kein Write).
  - --dry-run: nur Plan + Match-Set + Vorher/Nachher-Sample. KEIN Write.
  - --write (nur biz): Backup (alte uid|value -> Datei) + transaktional (begin/commit/rollback).

Usage: patch_ai_de_dims.py --dry-run   |   patch_ai_de_dims.py --write   (Quelle/Ziel immer biz)
"""
import os, re, json, argparse
from decimal import Decimal, ROUND_HALF_UP
import importlib.util
DEPLOY = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rollout", os.path.join(DEPLOY, "rollout.py"))
ROLL = importlib.util.module_from_spec(spec); spec.loader.exec_module(ROLL)
import pymysql

GP_TABLE = "tx_cartgigapixels_domain_model_gigapixel"
OUT = os.path.expanduser("~/gigapixel-exchange/es-catalog-promote")

# Dims-Span: W (sep) H + optionale Einheit. Tausender = . / Space / NBSP.
DIM_RE = re.compile(r'(\d[\d.   ]*\d|\d)\s*([×x*])\s*(\d[\d.   ]*\d|\d)(\s*(?:Pixel|px|Px|PX))?')
# GP-Span: Zahl (Komma- ODER Punkt-Dezimal) + (Space/Bindestrich) + Einheit.
# Punkt-Dezimal "0.14" kommt im Korpus vor — muss als 0,14 erkannt (nicht als "14") werden;
# Bindestrich-Form "1,87-Gigapixel-Aufnahme" ebenfalls.
GP_RE  = re.compile(r'(\d+(?:[.,]\d+)?)(\s*-?\s*)(Gigapixel|GP|gigap[íi]xel|Gigap[íi]xel)')

def _db(target, autocommit):
    ROLL._load_secrets()
    T = target.upper()
    return pymysql.connect(host=os.environ[f"DB_{T}_HOST"], user=os.environ[f"DB_{T}_USER"],
        password=os.environ[f"DB_{T}_PASSWORD"], database=os.environ[f"DB_{T}_NAME"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=autocommit)

def _digits(s): return int(re.sub(r'\D', '', s))
def _style(raw):
    if '.' in raw: return ('.', raw[raw.index('.')])  # dot-thousands
    m = re.search(r'\d([   ])\d', raw)
    if m: return ('sp', m.group(1))                    # space-thousands (genauer Char erhalten)
    return ('none', '')
def _fmt(n, style):
    s = str(n)
    if style[0] == 'none': return s
    sep = '.' if style[0] == '.' else style[1]
    out = ''
    while len(s) > 3:
        out = sep + s[-3:] + out; s = s[:-3]
    return s + out
def _gp_true(w, h):
    g = (Decimal(w) * Decimal(h)) / Decimal(10**9)
    return str(g.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)).replace('.', ',')
def _dim_pair(text):
    m = DIM_RE.search(text or '')
    return (_digits(m.group(1)), _digits(m.group(3))) if m else None
def _gp_val(text):
    m = GP_RE.search(text or '')
    return m.group(1) if m else None

def patch_text(text, w, h):
    """Chirurgisch: Maß-Span (falls ≠ truth) + GP-Span (auf truth) ersetzen. Rest unberührt."""
    truth = (w, h); gpt = _gp_true(w, h)
    def gp_sub(m):
        num, sp, unit = m.group(1), m.group(2), m.group(3)
        # Dezimal-Separator des Originals erhalten (Punkt-Original "0.14" -> Punkt-Ausgabe).
        out = gpt.replace(',', '.') if ('.' in num and ',' not in num) else gpt
        return out + sp + unit
    # Maß spacing-/stiltreu neu bauen (nur Ziffern ersetzt, Separator/Spacing/Einheit erhalten)
    def dim_sub_exact(m):
        wa, sep, ha, unit = m.group(1), m.group(2), m.group(3), (m.group(4) or '')
        if {_digits(wa), _digits(ha)} == set(truth):
            return m.group(0)
        left  = m.group(0)[:m.start(2)-m.start(0)]      # alles bis Separator (inkl. evtl. Space)
        # Original-Spacing um den Separator rekonstruieren
        gap_l = re.search(r'(\s*)$', m.group(0)[:m.start(2)-m.start(0)]).group(1)
        gap_r = re.search(r'^(\s*)', m.group(0)[m.end(2)-m.start(0):]).group(1)
        return _fmt(w, _style(wa)) + gap_l + sep + gap_r + _fmt(h, _style(ha)) + unit
    new = DIM_RE.sub(dim_sub_exact, text, count=1)
    new = GP_RE.sub(gp_sub, new, count=1)
    return new, truth, gpt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--target", choices=["biz", "gmbh"], default="biz",
                    help="DB-Ziel (DB_<TARGET>_*); gmbh ist LIVE")
    ap.add_argument("--column", default="ai_description_de",
                    choices=["ai_description_de", "ai_description_en"],
                    help="zu patchende Prosa-Spalte (Maße/GP); Wahrheit bleibt format_width/height")
    a = ap.parse_args()
    if a.write == a.dry_run:
        print("Genau eines von --dry-run / --write angeben."); return
    COL = a.column
    SFX = ("" if a.target == "biz" else f"_{a.target}") + ("" if COL == "ai_description_de" else "_en")
    print(f"patch_ai_de_dims: target={a.target}{' [LIVE]' if a.target=='gmbh' else ''}  mode={'WRITE' if a.write else 'DRY-RUN'}")
    c = _db(a.target, autocommit=False); cur = c.cursor()
    cur.execute(f"SELECT uid, {COL} de, format_width fw, format_height fh "
                f"FROM {GP_TABLE} WHERE deleted=0 AND {COL}<>''")
    rows = cur.fetchall()

    affected = []   # (uid, old, new, truth, gpt)
    skipped  = []   # (uid, reason)
    for r in rows:
        d = dict(r); de = d['de']; w, h = d['fw'] or 0, d['fh'] or 0
        if not w or not h: continue
        truth = (w, h); tgp = _gp_true(w, h)
        dp = _dim_pair(de); gpv = _gp_val(de)
        dims_wrong = dp is not None and set(dp) != set(truth)
        gp_wrong   = dp is not None and set(dp) == set(truth) and gpv is not None and gpv.replace('.', ',') != tgp
        if not (dims_wrong or gp_wrong):
            continue
        new, _, gpt = patch_text(de, w, h)
        # Validierung: aus NEUEM Text re-extrahieren -> Truth?
        nd = _dim_pair(new); ng = _gp_val(new)
        ok_dims = (nd is not None and set(nd) == set(truth))
        # GP nur validieren, wenn das Original ein GP-Token trägt (DIGITAL_GRAFIK hat oft nur Maß, keine GP).
        ok_gp   = (gpv is None) or (ng is not None and ng.replace('.', ',') == tgp)
        # Skeleton-Check: ausserhalb der Zahl-Tokens byte-identisch. Alle Zahl-Formatzeichen
        # (Ziffern, Punkt, Komma, Whitespace) wegstrippen -> die uebrige Prosa MUSS gleich sein.
        nonnum_old = re.sub(r'[\d.,\s]', '', de); nonnum_new = re.sub(r'[\d.,\s]', '', new)
        if not (ok_dims and ok_gp and new != de and nonnum_old == nonnum_new):
            skipped.append((d['uid'], f"validate dims={ok_dims} gp={ok_gp} changed={new!=de} skel={nonnum_old==nonnum_new}"))
            continue
        affected.append((d['uid'], de, new, truth, gpt))

    os.makedirs(OUT, exist_ok=True)
    # Match-Set (alle betroffenen, Vorher-Zustand)
    with open(OUT+f"/dims_patch_matchset{SFX}.tsv", "w", encoding="utf-8") as f:
        f.write("uid\told_dims\told_gp\ttruth_dims\ttruth_gp\n")
        for uid, old, new, truth, gpt in affected:
            f.write(f"{uid}\t{_dim_pair(old)}\t{_gp_val(old)}\t{truth[0]}x{truth[1]}\t{gpt}\n")

    print(f"Records (mit ai_de+fmt): {len(rows)}")
    print(f"  zu patchen (validiert): {len(affected)}")
    print(f"  SKIPPED (Validierung fehlgeschlagen → NICHT angefasst): {len(skipped)}")
    for uid, why in skipped[:20]: print(f"    skip uid {uid}: {why}")

    # Diverses Vorher/Nachher-Sample
    def pick_diverse(items, n=15):
        seen=set(); out=[]
        for it in items:
            uid, old, new, truth, gpt = it
            key=( '×' if '×' in old else ('x' if re.search(r'\dx\d|\d x \d', old) else '?'),
                  'Gigapixel' if 'Gigapixel' in old else ('GP' if 'GP' in old else '?'),
                  'dot' if '.' in (old.split(' Pixel')[0][-15:]) else 'plain')
            if key not in seen or len(out)<n:
                seen.add(key); out.append(it)
            if len(out)>=n: break
        return out
    with open(OUT+f"/dims_patch_sample{SFX}.txt", "w", encoding="utf-8") as f:
        f.write(f"DIMS-PATCH Vorher/Nachher — {len(affected)} betroffen, diverses Sample\n\n")
        for uid, old, new, truth, gpt in pick_diverse(affected, 15):
            f.write(f"=== uid {uid}  (truth {truth[0]}×{truth[1]} = {gpt} GP) ===\nALT: {old}\nNEU: {new}\n\n")
    print("written:", OUT+f"/dims_patch_sample{SFX}.txt", f"+ dims_patch_matchset{SFX}.tsv")

    if a.dry_run:
        print("\n=== DRY-RUN — KEIN Write ===")
        c.close(); return

    # --- WRITE (biz) ---
    ts = ROLL  # placeholder; timestamp via SQL NOW-ähnlich nicht nötig
    backup = OUT+f"/dims_patch_backup{SFX}.tsv"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(f"uid\told_{COL}\n")
        for uid, old, new, truth, gpt in affected:
            f.write(f"{uid}\t{json.dumps(old, ensure_ascii=False)}\n")
    print(f"Backup geschrieben: {backup} ({len(affected)} Records)")
    try:
        c.begin()
        for uid, old, new, truth, gpt in affected:
            cur.execute(f"UPDATE {GP_TABLE} SET {COL}=%s WHERE uid=%s AND {COL}=%s",
                        (new, uid, old))
        c.commit()
        print(f"COMMIT ok — {len(affected)} {COL} gepatcht.")
    except Exception as e:
        c.rollback(); print("ROLLBACK -", repr(e)); raise
    finally:
        c.close()

if __name__ == "__main__":
    main()
