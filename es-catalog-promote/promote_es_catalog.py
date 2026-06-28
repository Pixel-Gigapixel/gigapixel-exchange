#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scoped-Copy der ES-Produktkatalog-Übersetzungen (tx_gigapixels_translation, language='es')
biz → Ziel (gmbh), transaktional. Kopiert NUR es-Rows (3 fields: title/keywords/description),
STRIPPT die eigene uid (Ziel vergibt neu via AUTO_INCREMENT — biz-es-uids sind die jüngsten und
würden sonst mit dem gmbh-Bestand kollidieren). Das Frontend-Lookup geht über
(source_table, source_uid, field, language), NICHT über uid → der uid-Wert ist funktional egal.

Read-only verifizierte Voraussetzungen:
  - Schema biz==gmbh für tx_gigapixels_translation (Spalten/Indizes identisch).
  - Produkt-uid-Identität biz↔gmbh (tx_cartgigapixels_domain_model_gigapixel: count 8889, max 9091,
    sku+title bei Stichproben-uids gleich) → source_uid löst auf gmbh dasselbe Produkt auf.
  - gmbh hat 0 es-Rows (Idempotenz).

Quelle IMMER biz (DB_BIZ_*). Ziel via --target {gmbh} (DB_GMBH_*). --dry-run schreibt NICHTS (nur Plan+Counts).
Idempotenz-Guard: Abbruch, wenn das Ziel schon es-Rows hat. Verify-in-TX VOR Commit; Mismatch → Rollback.
"""
import os, argparse, importlib.util
DEPLOY = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rollout", os.path.join(DEPLOY, "rollout.py"))
ROLL = importlib.util.module_from_spec(spec); spec.loader.exec_module(ROLL)
import pymysql

TR     = "tx_gigapixels_translation"
LANG   = "es"
EXPECT = {"title": 8760, "keywords": 8823, "description": 8889}     # erwartete es-Counts je field
COPY_COLS = ["source_table", "source_uid", "field", "language", "value", "source_hash", "tstamp"]  # uid NICHT
BATCH  = 500

def _db(prefix, autocommit):
    ROLL._load_secrets()
    return pymysql.connect(host=os.environ[f"DB_{prefix}_HOST"], user=os.environ[f"DB_{prefix}_USER"],
        password=os.environ[f"DB_{prefix}_PASSWORD"], database=os.environ[f"DB_{prefix}_NAME"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=autocommit)

def _counts_by_field(cur):
    cur.execute(f"SELECT field, COUNT(*) n FROM {TR} WHERE language=%s GROUP BY field", (LANG,))
    return {r['field']: r['n'] for r in cur.fetchall()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["gmbh"], required=True, help="Ziel (nur gmbh; Quelle ist immer biz)")
    ap.add_argument("--dry-run", action="store_true", help="nur Plan+Counts, KEIN Write ins Ziel")
    a = ap.parse_args()
    DST = a.target.upper()
    print(f"promote_es_catalog: biz → {DST}{' [LIVE]' if DST=='GMBH' else ''}  mode={'DRY-RUN' if a.dry_run else 'WRITE'}")

    src = _db("BIZ", autocommit=True)
    dst = _db(DST, autocommit=False)
    sc, dc = src.cursor(), dst.cursor()
    try:
        # --- Soll-Ist (Quelle) ---
        sbf = _counts_by_field(sc)
        print("  biz es je field:", sbf)
        for f, exp in EXPECT.items():
            print(f"    {f}: {sbf.get(f,0)} (erwartet {exp}) {'✓' if sbf.get(f,0)==exp else '✗ MISMATCH'}")
        if any(sbf.get(f,0) != exp for f, exp in EXPECT.items()):
            print("ABBRUCH: Quelle weicht von erwarteten Counts ab."); return

        # --- Idempotenz-Guard (Ziel muss es=0 haben) ---
        dbf = _counts_by_field(dc)
        if sum(dbf.values()):
            print(f"ABBRUCH (Idempotenz): Ziel hat schon es-Rows: {dbf}"); return

        # --- Schema-Parität ---
        sc.execute(f"SHOW COLUMNS FROM {TR}"); scols = [r['Field'] for r in sc.fetchall()]
        dc.execute(f"SHOW COLUMNS FROM {TR}"); dcols = [r['Field'] for r in dc.fetchall()]
        if scols != dcols:
            print(f"ABBRUCH: Schema-Drift Spalten\n  biz ={scols}\n  gmbh={dcols}"); return
        missing = [c for c in COPY_COLS if c not in dcols]
        if missing:
            print(f"ABBRUCH: Zielspalten fehlen: {missing}"); return

        # --- Quelle lesen ---
        sc.execute(f"SELECT {','.join('`'+c+'`' for c in COPY_COLS)} FROM {TR} "
                   f"WHERE language=%s ORDER BY field, source_uid", (LANG,))
        rows = sc.fetchall()
        total = len(rows)
        print(f"  Quelle gelesen: {total} es-Rows (erwartet {sum(EXPECT.values())}) "
              f"{'✓' if total==sum(EXPECT.values()) else '✗'}")

        if a.dry_run:
            print(f"\n=== DRY-RUN: würde {total} Rows inserten (uid gestrippt → AUTO_INCREMENT, "
                  f"Cols={COPY_COLS}) — KEIN Write ===")
            return

        # --- Transaktionaler Insert (batched) ---
        dst.begin()
        sql = (f"INSERT INTO {TR} (" + ",".join(f"`{c}`" for c in COPY_COLS) + ") "
               "VALUES (" + ",".join(["%s"] * len(COPY_COLS)) + ")")
        buf = []
        for r in rows:
            buf.append([r[c] for c in COPY_COLS])
            if len(buf) >= BATCH:
                dc.executemany(sql, buf); buf = []
        if buf:
            dc.executemany(sql, buf)

        # --- Verify IN-TX (vor Commit) ---
        vbf = _counts_by_field(dc)
        print("  Verify (in TX, vor Commit):", vbf)
        if any(vbf.get(f,0) != exp for f, exp in EXPECT.items()):
            dst.rollback(); print("ROLLBACK — Verify-Mismatch, KEIN Commit."); return
        dst.commit()
        print("COMMIT ok.")
        for f, exp in EXPECT.items():
            print(f"  Verify {f}: {vbf.get(f,0)} (erwartet {exp}) {'✓' if vbf.get(f,0)==exp else '✗ MISMATCH'}")
    except Exception as e:
        try: dst.rollback()
        except Exception: pass
        print("ROLLBACK -", repr(e)); raise
    finally:
        src.close(); dst.close()

if __name__ == "__main__":
    main()
