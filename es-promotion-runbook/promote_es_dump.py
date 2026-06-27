#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scoped-Copy der ES-Schicht (sys_language_uid=4) biz → Ziel (gmbh), transaktional.
Kopiert NUR lang4-Rows aus 4 Tabellen, STRIPPT die eigene uid (Ziel vergibt neu via AUTO_INCREMENT).
l10n_parent / l18n_parent / pid / category / l10n_source / t3_origuid bleiben = DE-uid → Identity-Parität
biz↔gmbh (bestätigt) → lösen 1:1 auf. KEINE sys_file_reference nötig (lang4-Refs = 0, ES erbt Bilder vom DE-Parent).

Quelle IMMER biz (DB_BIZ_*). Ziel via --target {gmbh} (env DB_GMBH_*). --dry-run schreibt NICHTS (nur Plan+Counts).
Idempotenz-Guard: bricht ab, wenn das Ziel in EINER der 4 Tabellen schon lang4 hat.
"""
import os, argparse, importlib.util
DEPLOY = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rollout", os.path.join(DEPLOY, "rollout.py"))
ROLL = importlib.util.module_from_spec(spec); spec.loader.exec_module(ROLL)
import pymysql

TABLES = [   # Reihenfolge unkritisch (alle Parent-Pointer sind DE-uids), aber stabil gehalten
    ("pages",                                        107),
    ("tt_content",                                   232),
    ("tx_gigapixelglossary_domain_model_term",        55),
    ("tx_gigapixelglossary_domain_model_category",     7),
]

def _db(prefix, autocommit):
    ROLL._load_secrets()
    return pymysql.connect(host=os.environ[f"DB_{prefix}_HOST"], user=os.environ[f"DB_{prefix}_USER"],
        password=os.environ[f"DB_{prefix}_PASSWORD"], database=os.environ[f"DB_{prefix}_NAME"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=autocommit)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["gmbh"], required=True, help="Ziel-System (nur gmbh; Quelle ist immer biz)")
    ap.add_argument("--dry-run", action="store_true", help="nur Plan+Counts, KEIN Write ins Ziel")
    a = ap.parse_args()
    DST = a.target.upper()
    print(f"promote_es_dump: biz → {DST}{' [LIVE]' if DST=='GMBH' else ''}  mode={'DRY-RUN' if a.dry_run else 'WRITE'}")

    src = _db("BIZ", autocommit=True)
    dst = _db(DST, autocommit=False)
    sc, dc = src.cursor(), dst.cursor()

    # --- Idempotenz-Guard (Ziel muss in allen 4 Tabellen lang4=0 haben) ---
    blockers = []
    for t, _ in TABLES:
        dc.execute(f"SELECT COUNT(*) n FROM {t} WHERE sys_language_uid=4"); n = dc.fetchone()['n']
        if n: blockers.append(f"{t}={n}")
    if blockers:
        print("ABBRUCH (Idempotenz): Ziel hat schon lang4:", ", ".join(blockers)); dst.close(); src.close(); return

    plan = []   # (table, n_source)
    try:
        if not a.dry_run:
            dst.begin()
        for t, exp in TABLES:
            sc.execute(f"SELECT * FROM {t} WHERE sys_language_uid=4 AND deleted=0 ORDER BY uid")
            rows = sc.fetchall()
            plan.append((t, len(rows)))
            if a.dry_run:
                # Spalten-/Parent-Check exemplarisch
                sample = rows[0] if rows else {}
                par = {k: sample.get(k) for k in ("l10n_parent", "l18n_parent", "pid", "category") if k in sample}
                print(f"  {t:<46} {len(rows)} Rows (erwartet {exp}) {'✓' if len(rows)==exp else '✗'}  Parent-Beispiel: {par}")
                continue
            for r in rows:
                r.pop("uid", None)                       # eigene uid strippen → Ziel vergibt neu
                cols = list(r.keys())
                sql = (f"INSERT INTO {t} (" + ",".join(f"`{c}`" for c in cols) + ") "
                       "VALUES (" + ",".join(["%s"] * len(cols)) + ")")
                dc.execute(sql, [r[c] for c in cols])
        if a.dry_run:
            print(f"\n=== DRY-RUN: würde inserten {[ (t,n) for t,n in plan ]} — KEIN Write ===")
        else:
            dst.commit()
            print("COMMIT ok.")
            for t, exp in TABLES:
                dc.execute(f"SELECT COUNT(*) n FROM {t} WHERE sys_language_uid=4"); n = dc.fetchone()['n']
                print(f"  Verify {t:<46} lang4={n}  (erwartet {exp})  {'✓' if n==exp else '✗ MISMATCH'}")
    except Exception as e:
        if not a.dry_run: dst.rollback()
        print("ROLLBACK -", repr(e)); raise
    finally:
        src.close(); dst.close()

if __name__ == "__main__":
    main()
