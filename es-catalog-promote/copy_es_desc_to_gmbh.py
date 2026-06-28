#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gezielter UPDATE der gmbh es-description-Rows aus den KORRIGIERTEN biz-Werten (Dims-Fix Schritt 5).
NICHT promote_es_catalog (dessen Idempotenz-Guard bräche ab — gmbh hat schon 26.472 es-Rows).
Kopiert für die 1.558 betroffenen source_uids den biz-Wert (value + source_hash) in die BESTEHENDE
gmbh-Row (field='description' AND language='es'). Match exakt per source_uid.

Sicherheit:
  - Ziel-Menge = die 1.558 uids aus dims_patch_matchset.tsv (biz-Match-Set, == gmbh-Match-Set verifiziert).
  - Pro uid: genau EINE gmbh-Row (source_uid, field, language) erwartet; sonst Abbruch.
  - --dry-run: Plan + Before/After-Sample (inkl. uid 4578 + 2309). KEIN Write.
  - --write: Backup gmbh-alt (uid|value) + transaktional; Verify == 1.558 (gmbh-value == biz-value).
"""
import os, csv, json, argparse, importlib.util
DEPLOY = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rollout", os.path.join(DEPLOY, "rollout.py"))
ROLL = importlib.util.module_from_spec(spec); spec.loader.exec_module(ROLL)
import pymysql

TR  = "tx_gigapixels_translation"
OUT = os.path.expanduser("~/gigapixel-exchange/es-catalog-promote")
MATCHSET = OUT + "/dims_patch_matchset.tsv"   # biz, 1558 uids
SAMPLE_FORCE = [4578, 2309]                    # die deterministisch gefixten -> im Sample zeigen

def _db(target, autocommit):
    ROLL._load_secrets(); T = target.upper()
    return pymysql.connect(host=os.environ[f"DB_{T}_HOST"], user=os.environ[f"DB_{T}_USER"],
        password=os.environ[f"DB_{T}_PASSWORD"], database=os.environ[f"DB_{T}_NAME"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=autocommit)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.write == a.dry_run:
        print("Genau eines von --dry-run / --write."); return
    print(f"copy_es_desc_to_gmbh: biz → gmbh [LIVE]  mode={'WRITE' if a.write else 'DRY-RUN'}")

    uids = sorted(int(r["uid"]) for r in csv.DictReader(open(MATCHSET), delimiter="\t"))
    print(f"  Ziel-uids (aus Match-Set): {len(uids)}")
    fmt = ",".join(["%s"] * len(uids))

    src = _db("biz", autocommit=True)
    dst = _db("gmbh", autocommit=False)
    sc, dc = src.cursor(), dst.cursor()

    # biz korrigierte Werte
    sc.execute(f"SELECT source_uid uid, value, source_hash FROM {TR} "
               f"WHERE field='description' AND language='es' AND source_uid IN ({fmt})", uids)
    biz = {r['uid']: (r['value'], r['source_hash']) for r in sc.fetchall()}
    # gmbh aktuelle Werte (+ Row-Existenz/Eindeutigkeit)
    dc.execute(f"SELECT source_uid uid, COUNT(*) n FROM {TR} "
               f"WHERE field='description' AND language='es' AND source_uid IN ({fmt}) GROUP BY source_uid", uids)
    gmbh_n = {r['uid']: r['n'] for r in dc.fetchall()}
    dc.execute(f"SELECT source_uid uid, value FROM {TR} "
               f"WHERE field='description' AND language='es' AND source_uid IN ({fmt})", uids)
    gmbh_old = {r['uid']: r['value'] for r in dc.fetchall()}

    # Konsistenz-Guards
    miss_biz  = [u for u in uids if u not in biz]
    miss_gmbh = [u for u in uids if u not in gmbh_n]
    dup_gmbh  = [u for u, n in gmbh_n.items() if n != 1]
    if miss_biz or miss_gmbh or dup_gmbh:
        print(f"ABBRUCH: miss_biz={miss_biz[:10]} miss_gmbh={miss_gmbh[:10]} dup_gmbh={dup_gmbh[:10]}")
        src.close(); dst.close(); return
    changed = [u for u in uids if gmbh_old.get(u) != biz[u][0]]
    print(f"  gmbh-Rows existieren+eindeutig: {len(uids)} ✓ · Werte verschieden (zu aktualisieren): {len(changed)}")

    # Sample
    sample = SAMPLE_FORCE + [u for u in changed if u not in SAMPLE_FORCE][:8]
    with open(OUT+"/dims_es_copy_sample.txt", "w", encoding="utf-8") as f:
        f.write(f"gmbh es-description UPDATE aus biz — {len(changed)}/{len(uids)} verschieden. WHERE: "
                f"field='description' AND language='es' AND source_uid IN (<1558>)\n\n")
        for u in sample:
            f.write(f"=== uid {u} ===\nGMBH-ALT: {gmbh_old.get(u)}\nBIZ-NEU : {biz[u][0]}\n\n")
    print("written:", OUT+"/dims_es_copy_sample.txt")

    if a.dry_run:
        print(f"\n=== DRY-RUN: würde {len(changed)} gmbh-es-Rows updaten (value+source_hash aus biz) — KEIN Write ===")
        src.close(); dst.close(); return

    # WRITE
    json.dump([{"uid": u, "old": gmbh_old.get(u)} for u in changed],
              open(OUT+"/dims_es_copy_backup_gmbh.json", "w"), ensure_ascii=False)
    try:
        dst.begin()
        for u in changed:
            val, sh = biz[u]
            dc.execute(f"UPDATE {TR} SET value=%s, source_hash=%s "
                       f"WHERE source_uid=%s AND field='description' AND language='es'", (val, sh, u))
        # Verify IN-TX
        dc.execute(f"SELECT source_uid uid, value FROM {TR} "
                   f"WHERE field='description' AND language='es' AND source_uid IN ({fmt})", uids)
        now = {r['uid']: r['value'] for r in dc.fetchall()}
        match = sum(1 for u in uids if now.get(u) == biz[u][0])
        print(f"  Verify (in TX): gmbh-value == biz-value für {match}/{len(uids)}")
        if match != len(uids):
            dst.rollback(); print("ROLLBACK — Verify < 1558."); return
        dst.commit(); print(f"COMMIT ok — {len(changed)} gmbh-es-Rows aktualisiert, {match}/{len(uids)} == biz.")
    except Exception as e:
        dst.rollback(); print("ROLLBACK -", repr(e)); raise
    finally:
        src.close(); dst.close()

if __name__ == "__main__":
    main()
