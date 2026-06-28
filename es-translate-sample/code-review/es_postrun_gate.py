#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ES Post-Run Full-Width-Gate (Teil B) — liest ungekappte ES-Ausgabe aus biz-DB.
Checks:
  (0) Coverage    : DE-Inhalt (deleted=0) ohne es-Zeile -> soll 0
  (1) DE-Residue  : GER-Wortset (wortgrenzen, accent-insensitiv) ueber ALLE es-title+es-keywords;
                    getrennt in ECHT (kleingeschrieben/standalone) vs FALSE-POSITIVE (bewahrter Eigenname)
  (2) Count-Drift : #DE-Keywords vs #ES-Keywords je Record; ES<DE = erwartete Dedup, ES>DE = Padding/Halluzination
  (3) gigapixel-Akzent: 'gigapixel' OHNE Akzent in es-Targets -> nur Marke (Gigapixel)/SKU erlaubt, sonst flaggen
  (4) Ueber-Leerung: leerer es-title trotz uebersetzbarem DE (DE!=EN) -> soll 0
Output: ~/gigapixel-exchange/es-translate-sample/postrun_gate.txt (+ flagged.tsv)
KEIN Write in die DB. Read-only.
"""
import os, re, unicodedata, csv
import rollout

def load_env():
    for l in open(os.path.expanduser("~/gigapixel-deploy/.env.local")):
        l=l.strip()
        if l and not l.startswith("#") and "=" in l:
            k,v=l.split("=",1); os.environ.setdefault(k, v.strip().strip('"').strip("'"))

GP="tx_cartgigapixels_domain_model_gigapixel"
TR="tx_gigapixels_translation"

# GER-Funktions-/Allerwelts-Wortset (Residue-Indikatoren; bewusst konservativ).
GER = set("""und oder aber der die das den dem des ein eine einer einem einen
mit ohne fuer von nicht nur auch bei aus auf im in am zum zur vor nach ueber unter
ansicht aussenansicht innenansicht nahaufnahme fernsicht detailansicht
baum baeume baumgruppe wald haus gebaeude kirche schloss bruecke berg see fluss
alt neu gross klein rot blau gelb gruen weiss schwarz
bluehender bluehend freigestellt wartezimmer haeuser strasse strassenrand wiese
gegen himmel morgen abend nebel""".split())

def norm(s):
    s=unicodedata.normalize("NFD", s or "")
    s="".join(c for c in s if unicodedata.category(c)!="Mn")  # strip accents
    return s.lower()

def toks_kw(s):
    return [t for t in re.split(r'[;,]', s or '') if t.strip()]

def main():
    load_env(); rollout.TARGET="BIZ"
    c=rollout._conn(); cur=c.cursor()
    # ES-Targets
    cur.execute(f"SELECT source_uid uid, field, value FROM {TR} WHERE language='es' AND field IN ('title','keywords')")
    es={}
    for r in cur.fetchall():
        d=dict(r); es.setdefault(d['uid'],{})[d['field']]=d['value'] or ''
    # DE-Quelle (nur lebende Records — deleted-Soft-Deletes überspringt der Command korrekt)
    cur.execute(f"SELECT uid, title, keywords FROM {GP} WHERE deleted=0")
    de={}
    for r in cur.fetchall():
        d=dict(r); de[d['uid']]=(d['title'] or '', d['keywords'] or '')
    # EN-Titel (für Check 4)
    cur.execute(f"SELECT source_uid uid, value FROM {TR} WHERE language='en' AND field='title'")
    en_title={}
    for r in cur.fetchall():
        d=dict(r); en_title[d['uid']]=(d['value'] or '')
    c.close()

    n_title=sum(1 for u in es if 'title' in es[u])
    n_kw   =sum(1 for u in es if 'keywords' in es[u])

    # (0) COVERAGE: DE-Inhalt vorhanden, aber keine es-Zeile (skipped/contract-fail)
    miss_title=[u for u,(t,k) in de.items() if t.strip() and 'title'    not in es.get(u,{})]
    miss_kw   =[u for u,(t,k) in de.items() if k.strip() and 'keywords' not in es.get(u,{})]

    # (4) empty-es-title trotz übersetzbarem DE (Über-Leerung; soll →0).
    # Korrekt leer = reiner Eigenname (DE==EN, sprachneutral). Falsch leer = DE≠EN (DE hat Inhalt).
    empty_with_en=[u for u,fields in es.items()
                   if 'title' in fields and not (fields['title'] or '').strip()
                   and en_title.get(u,'').strip()
                   and de.get(u,('',''))[0].strip() != en_title.get(u,'').strip()]

    # (1) DE-Residue — getrennt in ECHT vs FALSE-POSITIVE (bewahrter Eigenname, Regel 5).
    # FP, wenn der Treffer im Original-Case großgeschrieben ist (Schloss/Haus/See) ODER an ein
    # großgeschriebenes Nachbarwort grenzt (Eigennamen-Phrase: "Arena am Panometer").
    GERrx=re.compile(r'\b(' + '|'.join(map(re.escape, sorted(GER))) + r')\b')
    res_real=[]; res_fp=[]
    for u,fields in es.items():
        for fld in ('title','keywords'):
            v=fields.get(fld)
            if not v: continue
            hits=set(GERrx.findall(norm(v)))
            if not hits: continue
            real=[]
            for tok in sorted(hits):
                is_real=False
                for m in re.finditer(r'\b'+re.escape(tok)+r'\b', v, re.I):
                    w=v[m.start():m.end()]
                    before=v[:m.start()].rstrip(); after=v[m.end():].lstrip()
                    prev_cap=bool(before) and before.split()[-1][:1].isupper()
                    next_cap=bool(after) and after[:1].isupper()
                    if w[:1].isupper() or prev_cap or next_cap:
                        continue          # Eigennamen-Kontext → FP
                    is_real=True; break    # kleingeschrieben & standalone → echtes Residue
                if is_real: real.append(tok)
            if real: res_real.append((u,fld,real,v))
            else:     res_fp.append((u,fld,sorted(hits),v))

    # (2) Count-Drift (keywords) — Richtung zählt: ES<DE ist erwartete Dedup, ES>DE wäre Halluzination.
    es_less=[]; es_more=[]
    for u,fields in es.items():
        if 'keywords' not in fields: continue
        de_n=len(toks_kw(de.get(u,('',''))[1]))
        es_n=len(toks_kw(fields['keywords']))
        d=es_n-de_n
        if d < -2: es_less.append((u,de_n,es_n,d))
        elif d > 2: es_more.append((u,de_n,es_n,d))

    # (3) gigapixel ohne Akzent — Marke = Wort beginnt mit Grossbuchstabe 'Gigapixel'
    gpx=[]
    for u,fields in es.items():
        for fld in ('title','keywords'):
            v=fields.get(fld) or ''
            for m in re.finditer(r'\b[Gg]igapixel\w*', v):  # OHNE Akzent (kein í)
                w=m.group(0)
                # erlaubt: Marke 'Gigapixel' (Grossbuchstabe) als eigenstaendige Marke; SKU-Kontext
                allowed = w[0]=='G'  # Marke gross
                if not allowed:
                    gpx.append((u,fld,w,v[:80]))

    OUT=os.path.expanduser("~/gigapixel-exchange/es-translate-sample")
    with open(OUT+"/postrun_gate.txt","w",encoding="utf-8") as f:
        f.write("ES POST-RUN FULL-WIDTH-GATE (ungekappte DB-Ausgabe, biz)\n")
        f.write(f"ES-Targets: title={n_title} · keywords={n_kw}\n\n")
        f.write(f"(0) COVERAGE — DE-Inhalt aber KEINE es-Zeile (skipped/contract-fail, MD5-Re-Run holt sie):\n")
        f.write(f"    fehlende es-title: {len(miss_title)}  uids={miss_title[:40]}{' …' if len(miss_title)>40 else ''}\n")
        f.write(f"    fehlende es-keywords: {len(miss_kw)}  uids={miss_kw[:40]}{' …' if len(miss_kw)>40 else ''}\n\n")
        f.write(f"(1) DE-RESIDUE (von {n_title+n_kw} Feldern):\n")
        f.write(f"    ECHTES Residue (kleingeschrieben, standalone): {len(res_real)}\n")
        f.write(f"    False-Positive (bewahrter Eigenname, Regel 5 — Schloss/Haus/am/See): {len(res_fp)}\n")
        for u,fld,toks,v in res_real[:60]:
            f.write(f"    [ECHT {fld} {u}] {toks}  -> {v[:110]!r}\n")
        if len(res_real)>60: f.write(f"    … +{len(res_real)-60} weitere echte\n")
        f.write(f"\n(2) COUNT-DRIFT (keywords) — Richtung:\n")
        f.write(f"    ES < DE (Δ<-2, erwartete Dedup der DE-Synonym-/Stuffing-Ketten): {len(es_less)}\n")
        f.write(f"    ES > DE (Δ>2, potentielle Halluzination — relevant): {len(es_more)}\n")
        for u,dn,en,dl in sorted(es_more, key=lambda x:-x[3])[:60]:
            f.write(f"    uid {u}: DE={dn} ES={en} (Δ=+{dl})\n")
        f.write(f"\n(3) gigapixel OHNE Akzent (nicht-Marke): {len(gpx)} Treffer\n")
        for u,fld,w,ctx in gpx[:60]:
            f.write(f"    [{fld} {u}] {w!r}  ctx={ctx!r}\n")
        if len(gpx)>60: f.write(f"    … +{len(gpx)-60} weitere\n")
        f.write(f"\n(4) empty-es-title trotz EN vorhanden (Über-Leerung, soll →0): {len(empty_with_en)}\n")
        if empty_with_en:
            f.write(f"    uids={empty_with_en[:60]}{' …' if len(empty_with_en)>60 else ''}\n")
    # flagged.tsv (maschinell, fuer gezielten Re-Translate)
    with open(OUT+"/flagged.tsv","w",encoding="utf-8",newline="") as f:
        w=csv.writer(f,delimiter="\t"); w.writerow(["uid","check","field","detail"])
        for u in miss_title: w.writerow([u,"missing","title",""])
        for u in miss_kw:    w.writerow([u,"missing","keywords",""])
        for u in empty_with_en: w.writerow([u,"empty_with_en","title",""])
        for u,fld,toks,v in res_real: w.writerow([u,"residue_real",fld,"|".join(toks)])
        for u,dn,en,dl in es_more:    w.writerow([u,"drift_more","keywords",f"DE={dn};ES={en};d=+{dl}"])
        for u,fld,wd,ctx in gpx:      w.writerow([u,"gpx_accent",fld,wd])
    print(f"ES-Targets title={n_title} kw={n_kw}")
    print(f"(0) missing es-title={len(miss_title)} · missing es-keywords={len(miss_kw)}")
    print(f"(1) Residue: echt={len(res_real)} · FP-Eigenname={len(res_fp)}")
    print(f"(2) Drift: ES<DE(dedup)={len(es_less)} · ES>DE(halluz?)={len(es_more)}")
    print(f"(3) gpx-no-accent: {len(gpx)}")
    print(f"(4) empty-es-mit-EN: {len(empty_with_en)}")
    print("written:", OUT+"/postrun_gate.txt", "+ flagged.tsv")

if __name__=="__main__": main()
