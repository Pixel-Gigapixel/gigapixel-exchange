#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Glossar-Load (transaktional): 55 ES-Term-Rows (lang4) + 7 ES-Kategorie-Overlays + 2 ES-Plugin-Elemente.
Liest die reviewten term-*.json (Source-of-Truth) aus --review-dir, normalisiert gigapíxel/Gigapixel im
Anzeigetext (NICHT Slugs), inserted transaktional. Idempotenz-Guard: bricht ab, wenn lang4 schon existiert.
ES voll (long_definition+meta_description behalten — über FR/RU-Parität, per 'vollständig'-Mandat).

Ziel-System env-getrieben über --target {biz,gmbh} (Default biz=Staging; ohne --target trifft ein Lauf NIE Live):
  DB_{TARGET}_HOST/USER/PASSWORD/NAME  +  {TARGET}_SSH/{TARGET}_SSH_PORT/{TARGET}_APP_ROOT/{TARGET}_PHP
de_uid-Identity zwischen biz und gmbh → l10n_parent greift 1:1 (kein Re-Keying nötig).
"""
import os, re, json, glob, argparse, importlib.util

DEPLOY = os.path.dirname(os.path.abspath(__file__))
def _load(mod, path):
    spec = importlib.util.spec_from_file_location(mod, os.path.join(DEPLOY, path))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
R = _load("rollout", "rollout.py")   # _load_secrets, typo3_slug_segment, flush_cache (target-aware)
import pymysql

CAT_ES = {1: "Captura", 2: "Procesamiento", 3: "Producción", 4: "Impresión", 7: "Medios", 5: "Técnica", 6: "Aplicación"}

def normalize(t):
    """gigapíxel/Gigapixel: Gattungswort klein+Akzent, Marke/Portal (GmbH/portal/plataforma) groß behalten."""
    if not t:
        return t
    t = re.sub(r'\bGigap[ií]xeles\b', 'gigapíxeles', t)
    t = re.sub(r'\bgigapixeles\b', 'gigapíxeles', t)
    def rep(m):
        s, e = m.start(), m.end()
        after = m.string[e:e + 6]; before = m.string[max(0, s - 16):s].lower()
        if after.lstrip().startswith('GmbH') or 'portal' in before or 'plataforma' in before:
            return m.group(0)
        return 'gigapíxel'
    t = re.sub(r'\bGigap[ií]xel\b', rep, t)
    t = re.sub(r'\bgigapixel\b', 'gigapíxel', t)
    return t

def db(target):
    R._load_secrets()
    return pymysql.connect(
        host=os.environ[f"DB_{target}_HOST"], user=os.environ[f"DB_{target}_USER"],
        password=os.environ[f"DB_{target}_PASSWORD"], database=os.environ[f"DB_{target}_NAME"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["biz", "gmbh"], default="biz",
                    help="Ziel-System (Default biz=Staging; gmbh=LIVE)")
    ap.add_argument("--review-dir", default=os.path.expanduser("~/exports/es-glossar-review"),
                    help="Verzeichnis mit den reviewten term-*.json")
    a = ap.parse_args()
    TARGET = a.target.upper()
    OUT = os.path.expanduser(a.review_dir)
    print(f"glossar_load: target={TARGET}{' [LIVE]' if TARGET=='GMBH' else ''} review-dir={OUT}")

    conn = db(TARGET); c = conn.cursor()
    TT = "tt_content"; TERM = "tx_gigapixelglossary_domain_model_term"; CAT = "tx_gigapixelglossary_domain_model_category"

    # --- Idempotenz-Guard ---
    c.execute(f"SELECT COUNT(*) n FROM {TERM} WHERE sys_language_uid=4 AND deleted=0"); n_term = c.fetchone()['n']
    c.execute(f"SELECT COUNT(*) n FROM {CAT} WHERE sys_language_uid=4 AND deleted=0"); n_cat = c.fetchone()['n']
    c.execute(f"SELECT COUNT(*) n FROM {TT} WHERE pid IN (391,392) AND sys_language_uid=4 AND deleted=0"); n_pl = c.fetchone()['n']
    if n_term or n_cat or n_pl:
        print(f"ABBRUCH (Idempotenz): lang4 existiert bereits — Terme={n_term} Kat={n_cat} Plugin={n_pl}")
        conn.close(); return
    c.execute(f"SHOW COLUMNS FROM {TT} LIKE 'l10n_source'"); has_l10nsrc = bool(c.fetchall())

    c.execute(f"SELECT uid,category,is_methodology_term,robots,pid FROM {TERM} WHERE sys_language_uid=0 AND deleted=0")
    de_term = {r['uid']: r for r in c.fetchall()}

    try:
        conn.begin()
        # ---------- 55 TERME ----------
        term_uids = {}
        for f in sorted(glob.glob(os.path.join(OUT, "term-*.json"))):
            d = json.load(open(f, encoding="utf-8")); du = d["de_uid"]; src = de_term[du]
            row = dict(
                pid=src['pid'], deleted=0, hidden=0,
                sys_language_uid=4, l10n_parent=du, l10n_diffsource=None, l10n_state=None,
                title=normalize(d["title"]), slug=d["slug"], category=src['category'],
                short_definition=normalize(d["short_definition"]),
                long_definition=normalize(d["long_definition"]),
                related_terms=0, example_images=0, status='live', quarantine_until=0,
                source_type='', source_uid=None, generator_model='', reviewer_model='',
                reviewer_decision='', reviewer_notes=None, quality_score=0,
                is_methodology_term=src['is_methodology_term'],
                meta_description=normalize(d["meta_description"]),
                canonical_url='', robots=src['robots'] or 'index,follow',
                faq_items=normalize(d["faq_items"]), image_query='',
            )
            cols = list(row.keys()); vals = [row[k] for k in cols]
            sql = (f"INSERT INTO {TERM} (" + ",".join(f"`{k}`" for k in cols) + ",`tstamp`,`crdate`) "
                   "VALUES (" + ",".join(["%s"] * len(cols)) + ",UNIX_TIMESTAMP(),UNIX_TIMESTAMP())")
            c.execute(sql, vals); term_uids[du] = c.lastrowid
        # ---------- 7 KATEGORIEN ----------
        c.execute(f"SELECT uid,pid,sorting FROM {CAT} WHERE sys_language_uid=0 AND deleted=0")
        de_cat = {r['uid']: r for r in c.fetchall()}
        cat_uids = {}
        for cu, es in CAT_ES.items():
            src = de_cat[cu]
            sql = (f"INSERT INTO {CAT} (`pid`,`deleted`,`hidden`,`sys_language_uid`,`l10n_parent`,`sorting`,"
                   "`l10n_state`,`title`,`slug`,`description`,`tstamp`,`crdate`) "
                   "VALUES (%s,0,0,4,%s,%s,NULL,%s,%s,'',UNIX_TIMESTAMP(),UNIX_TIMESTAMP())")
            c.execute(sql, (src['pid'], cu, src['sorting'], es, R.typo3_slug_segment(es)))
            cat_uids[cu] = c.lastrowid
        # ---------- 2 PLUGIN-ELEMENTE (tt_content clone von 819/820) ----------
        plug_uids = {}
        for de_pl in (819, 820):
            c.execute(f"SELECT * FROM {TT} WHERE uid=%s", (de_pl,)); base = c.fetchone()
            base.pop('uid')
            base['sys_language_uid'] = 4; base['l18n_parent'] = de_pl
            if has_l10nsrc:
                base['l10n_source'] = de_pl
            cols = list(base.keys())
            sql = (f"INSERT INTO {TT} (" + ",".join(f"`{k}`" for k in cols) + ") VALUES (" +
                   ",".join("UNIX_TIMESTAMP()" if k in ('tstamp', 'crdate') else "%s" for k in cols) + ")")
            execvals = [base[k] for k in cols if k not in ('tstamp', 'crdate')]
            c.execute(sql, execvals); plug_uids[de_pl] = c.lastrowid
        conn.commit()
        print("COMMIT ok.")
        print(f"  Terme:  {len(term_uids)}  uid-Range {min(term_uids.values())}-{max(term_uids.values())}")
        print(f"  Kat:    {len(cat_uids)}   uids {sorted(cat_uids.values())}")
        print(f"  Plugin: 391<-{plug_uids[819]}  392<-{plug_uids[820]}")
        c.execute(f"SELECT COUNT(*) n FROM {TERM} WHERE sys_language_uid=4 AND deleted=0"); print("  Verify lang4 Terme:", c.fetchone()['n'])
        c.execute(f"SELECT COUNT(*) n FROM {CAT} WHERE sys_language_uid=4 AND deleted=0"); print("  Verify lang4 Kat:", c.fetchone()['n'])
    except Exception as e:
        conn.rollback(); print("ROLLBACK -", repr(e)); raise
    finally:
        conn.close()

    # Cache-Flush auf demselben Ziel (rollout.flush_cache ist TARGET-aware)
    R.TARGET = TARGET
    R.flush_cache(print)

if __name__ == "__main__":
    main()
