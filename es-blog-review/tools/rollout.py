#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rollout.py — automatisierter Sprach-Rollout fuer gigapixel TYPO3.
Pro Seite: DE selektieren -> uebersetzen (Claude + TRANSLATION_GUIDE.md) -> gates.py -> Donor-Klon-INSERT -> cache.
Skaliert den manuellen Phase-B-Flow auf Batches (z. B. Blog 201-389, Tier-2-Overlays).

=========================================================================================
GERUEST-STATUS — was Claude Code noch verdrahten muss (alles mit TODO[CC] markiert):
  1) db_query / db_execute_tx        -> bestehende DB-Anbindung (pymysql direkt ODER ssh+mysql wie bisher)  [DONE: pymysql -> biz]
  2) ensure_page_overlay()           -> pages-Overlay anlegen, WENN keins existiert (Blog!) — inkl. SLUG     [DONE]
  3) CACHE: am Ende `typo3 cache:flush` (voll) statt 13 cache_* einzeln — einfachste korrekte Variante       [DONE: flush_cache via ssh]
  4) build_insert(): Spaltenliste EXAKT aus der Donor-Row (column-name parity wie bei den manuellen INSERTs) [DONE]
Rest (Modell-Call, Gates, Dry-Run/Commit, CLI, Loop, Idempotenz, Logging) ist fertig.
=========================================================================================

ANBINDUNG (von Claude Code verdrahtet):
  - DB:    pymysql direkt auf die biz-DB (Host/User/Name/Passwort: <aus .env.local>).
           Credentials kommen aus ~/gigapixel-deploy/.env.local (DB_BIZ_HOST/USER/PASSWORD/NAME) — gitignored.
           Verbindung mit autocommit=1 (ueberschreibt KonsoleH-Default autocommit=OFF); Writes laufen in
           EXPLIZITER Transaktion (conn.begin()/commit(), Rollback bei Fehler).
  - Modell: Anthropic API. Key aus env ANTHROPIC_API_KEY, sonst aus Datei ~/.anthropic-api-key.
  - Cache:  ssh -p <BIZ_SSH_PORT> <BIZ_SSH> 'cd <BIZ_APP_ROOT> && <BIZ_PHP> -d memory_limit=512M vendor/bin/typo3 cache:flush'
           (BIZ_SSH/BIZ_SSH_PORT/BIZ_APP_ROOT: <aus .env.local> — kein Default im Code)

CLI:
  # Dry-Run: uebersetzen + gaten, ES-JSON je Seite in review-dir, KEIN Write  (IMMER zuerst!)
  python rollout.py --pids 201-389 --lang 4 --dry-run --review-dir ~/exports/es-review
  # Commit: uebersetzen + gaten + INSERT + cache
  python rollout.py --pids 391,392 --lang 4 --commit
  # Einzelseite
  python rollout.py --pids 45 --lang 4 --commit

SICHERHEIT:
  - --dry-run zuerst, ES-JSON reviewen, DANN --commit. (Bei Blog: Slugs im Dry-Run gegenpruefen!)
  - Idempotent: Seiten mit vollstaendigem ES-Overlay (es_ce==de_ce) werden uebersprungen (ausser --force).
  - Gate-Gate: KEIN INSERT ohne gruenes gates.py. Bei FAIL: 1x Retry mit Fehler-Feedback, sonst Seite flaggen.
  - INSERT in EXPLIZITER Transaktion (KonsoleH autocommit=OFF), Rollback bei Fehler.
  - Page-Overlay + zugehoerige Content-INSERTs laufen in EINER Transaktion (atomar: kein Overlay ohne Content).
  - Klont Donor (RU via (pid,colPos,sorting), sonst DE-Quelle = Mirror#5); nur Sprache+Text ueberschrieben.
  - Ruehrt DE-Quellzeilen NIE an. NICHT fuer Tier-1 (Recht/Menue) blind nutzen — die bleiben reviewte Einzel-Laeufe.
"""
import argparse, json, os, re, subprocess, sys, time, unicodedata
from collections import OrderedDict

import pymysql

# ---- Konfiguration ----
LANG_ISO   = {2: "fr", 3: "ru", 4: "es"}                 # nur fuer Logs/Slug-Hinweise
GUIDE_PATH = os.path.expanduser("~/gigapixel-deploy/tools/TRANSLATION_GUIDE.md")
GATES_PATH = os.path.expanduser("~/gigapixel-deploy/tools/gates.py")
ENV_LOCAL  = os.path.expanduser("~/gigapixel-deploy/.env.local")
APIKEY_FILE = os.path.expanduser("~/.anthropic-api-key")
DEFAULT_MODEL = "claude-sonnet-4-6"          # Qualitaet; fuer Masse/Blog ggf. claude-haiku-4-5-20251001 (Kosten)

# biz cache-flush (ssh): Infra-Identifier (BIZ_SSH/BIZ_SSH_PORT/BIZ_APP_ROOT) kommen AUSSCHLIESSLICH
# aus ~/gigapixel-deploy/.env.local (gitignored) — KEIN hartkodierter Fallback. Gelesen + fail-fast
# erst zur Nutzungszeit in flush_cache() (so bleibt `rollout.py --help` ohne env lauffaehig).
BIZ_PHP      = os.environ.get("BIZ_PHP", "php82.bin.cli")     # PHP-Binary (kein Infra-Identifier); CLI-Default 96 MB ist zu klein -> -d memory_limit=512M

# pages-Textfelder, die je Sprache verschieden sind: ES = uebersetzt(DE) bzw. leer wie DE — NIE vom RU-Donor erben.
# (Sonst landet russisches seo_title/description auf der spanischen Seite.)
PAGE_TRANSLATE = ["title", "nav_title", "seo_title", "description", "abstract",
                  "og_title", "og_description", "twitter_title", "twitter_description", "keywords"]
PAGE_MIRROR_TEXT = PAGE_TRANSLATE + ["canonical_link"]       # canonical NIE uebersetzen, aber DE spiegeln (leer)

# =========================================================================================
# ENV / SECRETS
# =========================================================================================
def _load_secrets():
    """Liest ~/gigapixel-deploy/.env.local (KEY=VALUE) nach os.environ (nur wenn noch nicht gesetzt)
    und holt ANTHROPIC_API_KEY notfalls aus ~/.anthropic-api-key. Idempotent."""
    if os.path.exists(ENV_LOCAL):
        for line in open(ENV_LOCAL, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    if not os.environ.get("ANTHROPIC_API_KEY") and os.path.exists(APIKEY_FILE):
        os.environ["ANTHROPIC_API_KEY"] = open(APIKEY_FILE, encoding="utf-8").read().strip()

def _require_env(name):
    """Infra-Identifier MUSS aus env/.env.local kommen — kein hartkodierter Fallback (fail-fast)."""
    v = os.environ.get(name)
    if not v:
        sys.exit(f"FEHLT: {name} nicht in env/.env.local gesetzt (Infra-Identifier — kein Default im Code).")
    return v

# =========================================================================================
# DB-LAYER  — pymysql direkt auf die biz-DB (TODO[CC] erledigt)
# =========================================================================================
_CONN = None
def _conn():
    """Lazy, prozessweite Verbindung zur biz-DB. autocommit=1 (ueberschreibt KonsoleH autocommit=OFF);
    Writes nehmen sich per conn.begin() eine explizite Transaktion."""
    global _CONN
    if _CONN is None:
        _load_secrets()
        _CONN = pymysql.connect(
            host=os.environ["DB_BIZ_HOST"], user=os.environ["DB_BIZ_USER"],
            password=os.environ["DB_BIZ_PASSWORD"], database=os.environ["DB_BIZ_NAME"],
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    return _CONN

def _reconnect():
    global _CONN
    try:
        if _CONN:
            _CONN.close()
    except Exception:
        pass
    _CONN = None

def db_query(sql, params=None):
    """SELECT -> Liste von dict-Rows. Reconnect+Retry 1x bei Verbindungsabbruch (lange Laeufe)."""
    for attempt in (1, 2):
        try:
            cur = _conn().cursor()
            cur.execute(sql, params or ())
            return cur.fetchall()
        except pymysql.err.OperationalError:
            if attempt == 2:
                raise
            _reconnect()

def db_execute_tx(statements):
    """statements: Liste (sql, params). In EINER Transaktion (begin ... commit), autocommit ist zwar 1,
    aber begin() oeffnet eine explizite TX; Rollback bei Fehler. Gibt Liste der neuen uids zurueck.
    Bei Verbindungsabbruch VOR dem commit: reconnect + ganze TX 1x neu (commit ist atomar-zuletzt -> sicher)."""
    for attempt in (1, 2):
        conn = _conn()
        new_uids = []
        try:
            conn.begin()
            cur = conn.cursor()
            for sql, params in statements:
                cur.execute(sql, params or ())
                new_uids.append(cur.lastrowid)
            conn.commit()
            return new_uids
        except pymysql.err.OperationalError:
            try:
                conn.rollback()
            except Exception:
                pass
            if attempt == 2:
                raise
            _reconnect()
        except Exception:
            conn.rollback()
            raise

# =========================================================================================
# MODELL-CALL  — Anthropic API
# =========================================================================================
def translate_fields(fields, guide, model, gate_feedback=None):
    """fields: OrderedDict der zu uebersetzenden Felder (header/subheader/bodytext; leere weglassen).
    Liefert dict mit uebersetzten Werten. Modell MUSS reines JSON zurueckgeben (nur die Schluessel)."""
    import anthropic
    _load_secrets()
    client = anthropic.Anthropic()
    system = guide + ("\n\n# AUSGABE-FORMAT (zwingend)\nGib AUSSCHLIESSLICH valides JSON zurueck mit "
                      "EXAKT den Eingabe-Schluesseln und uebersetzten Werten. Kein Text davor/danach, kein Markdown, "
                      "keine Code-Fence. HTML-Struktur, Zahlen, Waehrung, Symbole, &amp;, Marken byte-genau lassen.")
    user = "Uebersetze die Werte dieses JSON ins Spanische (es-ES) nach den Regeln des System-Prompts:\n"
    if gate_feedback:
        user = ("Die vorige Uebersetzung hat Gates verletzt. KORRIGIERE gezielt:\n" + gate_feedback +
                "\n\nHier erneut die Quelle, gib korrigiertes JSON:\n")
    user += json.dumps(fields, ensure_ascii=False)
    # Opus 4.8 lehnt das (deprecate) temperature-Feld ab; Sonnet bleibt deterministisch bei temperature=0.
    extra = {} if "opus-4-8" in model else {"temperature": 0}
    resp = client.messages.create(model=model, max_tokens=8192, system=system,
                                  messages=[{"role": "user", "content": user}], **extra)
    txt = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.S).strip()
    return json.loads(txt)

# =========================================================================================
# HELPERS
# =========================================================================================
def parse_pids(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out

def fetch_de_elements(pid):
    # SELECT * -> volle Spalten-Parity, falls die DE-Quelle als Donor einspringt (Mirror#5, kein RU-Overlay).
    return db_query(
        "SELECT * FROM tt_content WHERE pid=%s AND sys_language_uid=0 AND deleted=0 "
        "ORDER BY colPos, sorting", (pid,))

def find_donor(pid, colPos, sorting):
    rows = db_query(
        "SELECT * FROM tt_content WHERE pid=%s AND colPos=%s AND sorting=%s "
        "AND sys_language_uid=3 AND deleted=0 LIMIT 1", (pid, colPos, sorting))   # RU = langId 3
    return rows[0] if rows else None

def content_counts(pid, lang):
    de = db_query("SELECT COUNT(*) n FROM tt_content WHERE pid=%s AND sys_language_uid=0 AND deleted=0", (pid,))[0]["n"]
    es = db_query("SELECT COUNT(*) n FROM tt_content WHERE pid=%s AND sys_language_uid=%s AND deleted=0", (pid, lang))[0]["n"]
    return de, es

def page_overlay_exists(de_pid, lang):
    return bool(db_query("SELECT uid FROM pages WHERE l10n_parent=%s AND sys_language_uid=%s AND deleted=0 LIMIT 1",
                         (de_pid, lang)))

# ---- SLUG: gleiche Strategie wie FR/RU-Blog = aus dem (uebersetzten) Titel generiert ----------
# Belegt an den FR/RU-Overlays: slug = <Eltern-Pfad>/<slugify(uebersetzter Titel)>.
#   201 DE /blog/was-ist-gigapixel-fotografie -> FR /blog/qu-est-ce-que-la-photographie-gigapixel
# TYPO3 SlugHelper-Aequivalent fuer LATEINISCHE Zielsprachen (ES ist rein lateinisch, kein Kyrillisch noetig):
#   lowercase -> spezielle Umschrift (ae/oe/ue/ss + Akzente) -> NFKD-Fallback -> [^a-z0-9] -> '-'.
# Quer-Check: "Qu'est-ce que la photographie gigapixel" -> "qu-est-ce-que-la-photographie-gigapixel"  (= FR-Slug).
_TRANSLIT = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "á": "a", "à": "a", "â": "a", "ã": "a", "å": "a",
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "í": "i", "ì": "i", "î": "i", "ï": "i",
    "ó": "o", "ò": "o", "ô": "o", "õ": "o",
    "ú": "u", "ù": "u", "û": "u",
    "ñ": "n", "ç": "c", "ý": "y", "ÿ": "y",
}
def typo3_slug_segment(title):
    s = re.sub(r"<[^>]+>", "", title or "").lower()
    s = "".join(_TRANSLIT.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)                 # restliche Akzente -> ASCII
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")

def build_page_slug(de_slug, es_title):
    """Eltern-Pfad aus dem DE-Slug + slugify(ES-Titel). Root-Seiten -> '/<segment>'."""
    prefix = (de_slug or "").rsplit("/", 1)[0]
    seg = typo3_slug_segment(es_title)
    if not seg:
        return de_slug or ""                             # Fallback: DE-Slug (sollte nie eintreten)
    return prefix + "/" + seg

def dedupe_slug(slug, lang):
    """TYPO3-aequivalente Eindeutigkeit je Sprache: bei Kollision -1, -2, ... anhaengen."""
    base, i, s = slug, 0, slug
    while db_query("SELECT uid FROM pages WHERE slug=%s AND sys_language_uid=%s AND deleted=0 LIMIT 1", (s, lang)):
        i += 1; s = f"{base}-{i}"
    return s

# ---- Blog-Meta-Zeile DETERMINISTISCH lokalisieren (gp-blog-meta: Datum + Kategorie) ----------
# Sprach-keyed: TR/PL/IT/AR brauchen später nur je eine neue Monats-/Kategorie-Tabelle.
DATE_PAT = (r'(\d{1,2})\.\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|'
            r'Oktober|November|Dezember)\s+(\d{4})')
ES_MONTH = {"Januar": "enero", "Februar": "febrero", "März": "marzo", "April": "abril",
            "Mai": "mayo", "Juni": "junio", "Juli": "julio", "August": "agosto",
            "September": "septiembre", "Oktober": "octubre", "November": "noviembre",
            "Dezember": "diciembre"}
BLOG_MONTH = {4: ES_MONTH}                                   # lang -> Monatsnamen-Map
BLOG_CAT = {4: {                                            # lang -> Kategorie-Map (Keys = exakt die DE-Quell-Strings)
    "Technologie": "Tecnología",
    "Wirtschaft": "Economía",
    "Technik": "Técnica",
    "Business": "Negocios",
    "Naturbilder": "Imágenes de naturaleza",
    "Gesundheit": "Salud",
    "Vertrieb": "Ventas",
    "Wissenschaft": "Ciencia",
    "Produkt": "Producto",
    "Architektur": "Arquitectura",
    "Evidence-Based Design": "Diseño basado en evidencia",
    "Technologie & Differenzierung": "Tecnología y diferenciación",
    "Praxis und Anwendung": "Práctica y aplicación",
    "Natur & Wissenschaft": "Naturaleza y ciencia",
    "Technologie & Wissenschaft": "Tecnología y ciencia",
    "Praxis &amp; Anwendung": "Práctica &amp; aplicación",   # &amp; BEHALTEN — sonst G&-Gate-Fail
    "Spezialanwendungen": "Aplicaciones especiales",
    "Hospitality & Design": "Hostelería y diseño",
    "B2B": "B2B",
}}
UNMAPPED_BLOG_CATS = set()                                   # Laufzeit-Sammler: nie raten, an Daniel melden

def _localize_meta_inner(de_inner, lang):
    """Inneres HTML der DE-gp-blog-meta -> zielsprachlich: Datum reformatiert + Kategorie gemappt.
    Unbekannte Kategorie -> UNMAPPED_BLOG_CATS (DE-Wert bleibt stehen, wird gemeldet, NICHT geraten)."""
    month_map = BLOG_MONTH.get(lang, {})
    cat_map = BLOG_CAT.get(lang, {})
    spans = re.findall(r'<span>(.*?)</span>', de_inner, re.S)
    out = de_inner
    if spans:                                                # span[0] = Datum
        d0 = spans[0]
        d0_loc = re.sub(DATE_PAT,
                        lambda m: (f"{m.group(1)} de {month_map[m.group(2)]} de {m.group(3)}"
                                   if m.group(2) in month_map else m.group(0)),
                        d0)
        if d0_loc != d0:
            out = out.replace(f"<span>{d0}</span>", f"<span>{d0_loc}</span>", 1)
    if len(spans) >= 2:                                      # span[1] = Kategorie
        cat_raw = spans[1]; cat = cat_raw.strip()
        if cat in cat_map:
            out = out.replace(f"<span>{cat_raw}</span>", f"<span>{cat_map[cat]}</span>", 1)
        else:
            UNMAPPED_BLOG_CATS.add(cat)
    return out

def localize_blog_meta(es_html, de_html, lang):
    """Ersetzt die <p class="gp-blog-meta">…</p>-Zeile im ÜBERSETZTEN bodytext durch eine deterministisch
    aus der DE-QUELLE lokalisierte Version (das Modell übersetzt die Kategorie unzuverlässig -> DE ist die
    Wahrheit). Wirkt regex-scoped NUR auf die Meta-Zeile; Artikel-Prosa wird nie berührt."""
    if lang not in BLOG_MONTH:
        return es_html
    mde = re.search(r'<p class="gp-blog-meta">(.*?)</p>', de_html or "", re.S)
    if not mde:
        return es_html
    new_meta = f'<p class="gp-blog-meta">{_localize_meta_inner(mde.group(1), lang)}</p>'
    return re.sub(r'<p class="gp-blog-meta">.*?</p>', lambda _m: new_meta, es_html, count=1, flags=re.S)

def _page_overlay_stmt(de, donor, lang, text_values, slug):
    """Baut das pages-INSERT-Statement: RU-Donor klonen, Sprach-Textfelder aus text_values setzen
    (nie RU erben), nav_hide/doktype/slug gesetzt. text_values muss alle PAGE_MIRROR_TEXT-Keys liefern."""
    row = dict(donor)
    row.pop("uid", None)
    row["sys_language_uid"] = lang
    row["l10n_parent"] = de["uid"]
    row["l10n_source"] = de["uid"]
    for k in PAGE_MIRROR_TEXT:
        row[k] = text_values.get(k, de.get(k) or "")
    row["nav_hide"] = de.get("nav_hide")                   # Menue-Struktur von DE spiegeln
    row["doktype"]  = de.get("doktype")                    # doktype-Drift vermeiden
    row["slug"] = slug
    if "l10n_diffsource" in row:
        row["l10n_diffsource"] = ""
    now = int(time.time())
    for k in ("tstamp", "crdate", "SYS_LASTCHANGED"):
        if k in row:
            row[k] = now
    cols = list(row.keys())
    collist = ", ".join(f"`{c}`" for c in cols)               # Backticks: Identifier-Sicherheit (reservierte Wörter)
    sql = f"INSERT INTO pages ({collist}) VALUES ({', '.join(['%s'] * len(cols))})"
    return (sql, [row[c] for c in cols])

def ensure_page_overlay(de_pid, lang, guide, model, dry_run, review_dir, log):
    """WENN kein ES-pages-Overlay existiert (Fall: Blog 201-389), eins anlegen.
    Klont das RU-pages-Overlay (l10n_parent=de_pid, sys_language_uid=3) als Vorlage, ueberschreibt:
      sys_language_uid=lang, l10n_parent=l10n_source=de_pid, alle Sprach-Textfelder = UEBERSETZT(DE) bzw. leer wie DE
      (NIE vom RU-Donor erben -> kein russisches seo_title/description-Leck), nav_hide + doktype VON DER DE-QUELLE
      gespiegelt, SLUG aus dem uebersetzten Titel generiert (wie FR/RU-Blog).
    Returns (status, stmt):
      ("exists", None)  schon vorhanden
      ("plan",   None)  Dry-Run: Plan in review_dir/<iso>-<pid>.page.json geschrieben + Slug geloggt
      ("create", stmt)  Commit: INSERT-Statement (geht in dieselbe TX wie die Content-INSERTs)
      ("blocked",None)  kein RU-Donor / keine DE-Seite / Uebersetzung gescheitert -> Seite ueberspringen
    """
    if page_overlay_exists(de_pid, lang):
        return ("exists", None)

    de_rows = db_query("SELECT * FROM pages WHERE uid=%s AND deleted=0", (de_pid,))
    if not de_rows:
        log(f"  pid {de_pid}: DE-Seite nicht gefunden -> blocked"); return ("blocked", None)
    de = de_rows[0]

    donor_rows = db_query("SELECT * FROM pages WHERE l10n_parent=%s AND sys_language_uid=3 AND deleted=0 LIMIT 1",
                          (de_pid,))
    if not donor_rows:
        log(f"  pid {de_pid}: KEIN RU-pages-Overlay als Vorlage -> blocked (manuell anlegen, nicht raten)")
        return ("blocked", None)
    donor = donor_rows[0]

    # --- Sprach-Textfelder uebersetzen (nur die in der DE-Quelle nicht-leeren) ---
    fields = OrderedDict((k, de[k]) for k in PAGE_TRANSLATE if de.get(k))
    translated = {}
    if fields:
        try:
            translated = translate_fields(fields, guide, model)
        except Exception as e:
            log(f"  pid {de_pid}: Titel/Meta-Uebersetzung fehlgeschlagen ({e}) -> blocked"); return ("blocked", None)

    es_title = translated.get("title", de.get("title") or "")
    slug = dedupe_slug(build_page_slug(de.get("slug"), es_title), lang)
    text_values = {k: translated.get(k, de.get(k) or "") for k in PAGE_MIRROR_TEXT}   # ES = uebersetzt(DE) sonst DE -> nie RU

    log(f"  pid {de_pid}: PLAN ES-Overlay  title={es_title!r}  nav_title={text_values.get('nav_title')!r}")
    log(f"  pid {de_pid}: PLAN slug={slug}   (DE-slug={de.get('slug')}  nav_hide={de.get('nav_hide')}  doktype={de.get('doktype')}  RU-donor={donor.get('uid')})")

    if dry_run:
        os.makedirs(review_dir, exist_ok=True)
        p = os.path.join(review_dir, f"{LANG_ISO.get(lang, lang)}-{de_pid}.page.json")
        plan = {"de_pid": de_pid, "slug": slug, "nav_hide": de.get("nav_hide"), "doktype": de.get("doktype"),
                "donor_ru_uid": donor.get("uid")}
        for k in PAGE_TRANSLATE:
            plan[k] = text_values.get(k)
        json.dump(plan, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return ("plan", None)

    return ("create", _page_overlay_stmt(de, donor, lang, text_values, slug))

_GATES_MOD = None
def _gates_mod():
    """gates.py einmalig in-process laden (fuer humanize_gate_feedback — run_gates selbst bleibt subprocess)."""
    global _GATES_MOD
    if _GATES_MOD is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gates_mod", GATES_PATH)
        _GATES_MOD = importlib.util.module_from_spec(spec); spec.loader.exec_module(_GATES_MOD)
    return _GATES_MOD

def _sentences_with_tokens(html_text, tokens):
    """ES-bodytext (HTML) -> die SÄTZE, die eines der geflaggten deutschen Tokens enthalten, woertlich."""
    import html as _html
    txt = _html.unescape(re.sub(r"<[^>]+>", " ", html_text or ""))
    txt = re.sub(r"\s+", " ", txt).strip()
    out = []
    for s in re.split(r"(?<=[.!?])\s+", txt):
        low = s.lower()
        if any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in tokens):
            out.append(s.strip())
    return out[:6]

def humanize_gate_feedback(gout, de_payload, es_payload):
    """Macht den rohen gates.py-Output (Tabelle/Multisets) zu konkreten, handlungsleitenden Saetzen fuers Modell.
    Re-leitet die Verletzungen direkt aus den Payloads ab (robuster als gout zu parsen)."""
    G = _gates_mod()
    de = {e["de_uid"]: e["bodytext"] for e in de_payload}
    es = {e["de_uid"]: e["bodytext"] for e in es_payload}
    msgs = []
    for uid in de:
        d, t = de[uid], es.get(uid, "")
        # G3 — deutscher Residue: die betroffenen SAETZE woertlich vorhalten.
        prose_de = G.german(t, strip_quotes=True)
        if prose_de:
            sents = _sentences_with_tokens(t, set(prose_de))
            quoted = "  ".join(f"„{s}”" for s in sents) or f"(Tokens: {dict(__import__('collections').Counter(prose_de))})"
            msgs.append(f"[uid {uid}] Diese Sätze sind noch DEUTSCH — übersetze sie vollständig ins Spanische: {quoted}  "
                        "In Quellenblöcken (class=\"gp-blog-source\") nur Autor/Werktitel/Journal/Jahr im Original lassen; "
                        "erklärende/beschreibende Sätze MÜSSEN übersetzt werden.")
        # G2 — Zahl-Mismatch: Quelle vs. Ziel nennen, Skalenwort-Regel, NIE faelschen.
        dn, tn = G.nums(d), G.nums(t)
        if dn != tn:
            msgs.append(f"[uid {uid}] Zahl-Mismatch: die Quelle hat {dict(dn - tn)}, deine Übersetzung hat {dict(tn - dn)}. "
                        "Übernimm die Ziffernfolgen der QUELLE exakt; große Zahlen mit Skalenwort: Quell-Ziffer behalten + "
                        "Skalenwort (DE „1,6 Milliarden” → ES „1,6 mil millones”), die Zahl NICHT umschreiben. "
                        "Korrektheit vor Gate — Zahlen niemals „passend” machen.")
        # G1/Gsym/Gcur/G& — knapp benennen.
        if G.tag_seq(d) != G.tag_seq(t):
            msgs.append(f"[uid {uid}] HTML-Tag-Skelett weicht ab — Tags/Attribute/Reihenfolge byte-genau aus der Quelle "
                        "übernehmen, nur den Text zwischen den Tags übersetzen.")
        if G.syms(d) != G.syms(t):
            msgs.append(f"[uid {uid}] Symbol-Mismatch DE={dict(G.syms(d))} ES={dict(G.syms(t))} — Symbole (↑↓→✓✗⚠ …) byte-genau spiegeln.")
        if G.curr(d) != G.curr(t):
            msgs.append(f"[uid {uid}] Währungs-Token-Mismatch DE={dict(G.curr(d))} ES={dict(G.curr(t))} — Beträge/Symbole/ISO-Codes "
                        "($, USD, €, 3.000) byte-genau; nur Währungs-WÖRTER übersetzen (Dollar → dólares).")
        if G.amp(d) != G.amp(t):
            msgs.append(f"[uid {uid}] &amp;-Anzahl weicht ab (DE={G.amp(d)} ES={G.amp(t)}) — &amp; als &amp; behalten.")
    if not msgs:
        return gout
    return ("Deine vorige Übersetzung hat folgende Prüfungen verletzt. Korrigiere GEZIELT genau diese Punkte, "
            "sonst alles unverändert lassen:\n" + "\n".join("• " + m for m in msgs))

def run_gates(de_payload, es_payload, taglines=None):
    import tempfile
    f1 = tempfile.NamedTemporaryFile("w", suffix="_de.json", delete=False, encoding="utf-8")
    f2 = tempfile.NamedTemporaryFile("w", suffix="_es.json", delete=False, encoding="utf-8")
    json.dump(de_payload, f1, ensure_ascii=False); json.dump(es_payload, f2, ensure_ascii=False)
    f1.close(); f2.close()
    cmd = [sys.executable, GATES_PATH, f1.name, f2.name]
    if taglines:
        cmd += ["--taglines", ",".join(map(str, taglines))]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(f1.name); os.unlink(f2.name)
    return r.returncode == 0, (r.stdout + r.stderr)

def build_insert(donor_row, de_uid, lang, translated, pid):
    """Donor-Zeile klonen; nur Sprache + uebersetzte Textfelder ueberschreiben.
    FAL/pi_flexform/colPos/sorting bleiben aus dem Donor. Spaltenliste = EXAKT die Donor-Spalten
    (column-name parity wie bei den manuellen Phase-B-INSERTs; keine erfundenen/fehlenden Spalten).
    'translated' enthaelt header/subheader/bodytext bereits DE-gespiegelt (leer bleibt leer, NIE RU-Text)."""
    row = dict(donor_row)
    row.pop("uid", None)
    row["sys_language_uid"] = lang
    row["l18n_parent"] = de_uid               # tt_content nutzt die Alt-Schreibweise l18n_parent
    row["l10n_source"] = de_uid
    row["pid"] = pid
    if "l18n_diffsource" in row:
        row["l18n_diffsource"] = ""
    now = int(time.time())
    for k in ("tstamp", "crdate"):
        if k in row:
            row[k] = now
    for k, v in (translated or {}).items():
        if k in row:
            row[k] = v
    cols = list(row.keys())
    collist = ", ".join(f"`{c}`" for c in cols)               # Backticks: tt_content hat reservierte Wörter (recursive, …)
    sql = f"INSERT INTO tt_content ({collist}) VALUES ({', '.join(['%s'] * len(cols))})"
    return sql, [row[c] for c in cols]

def flush_cache(log):
    """Voller TYPO3-Cache-Flush auf biz via ssh (memory_limit hoch, CLI-Default ist zu klein)."""
    _load_secrets()
    ssh, ssh_port, app_root = _require_env("BIZ_SSH"), _require_env("BIZ_SSH_PORT"), _require_env("BIZ_APP_ROOT")
    remote = f"cd {app_root} && {BIZ_PHP} -d memory_limit=512M vendor/bin/typo3 cache:flush"
    log(f"cache:flush auf biz ({app_root}) ...")
    r = subprocess.run(["ssh", "-p", ssh_port, ssh, remote], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    log(out if out else f"(cache:flush exit {r.returncode})")
    if r.returncode != 0:
        log(f"WARN: cache:flush exit {r.returncode}")
    return r.returncode == 0

# =========================================================================================
# HAUPTLAUF
# =========================================================================================
def translate_page(de_elems, guide, model, pid, lang, log, gate_feedback=None):
    """Uebersetzt alle Content-Elemente einer Seite -> (de_payload, es_payload, inserts).
    gate_feedback (gates.py-Output aus Pass 1) wird beim Retry an translate_fields durchgereicht,
    damit das Modell den konkreten Fehler korrigiert (z. B. '6->600' / 'gp-blog-source-Block uebersetzen').
    ES-Werte = uebersetzt, sonst DE-Wert (leer bleibt leer) -> NIE den RU-Donor-Text erben.
    Die gp-blog-meta-Zeile wird danach DETERMINISTISCH aus der DE-Quelle lokalisiert (Datum+Kategorie)."""
    de_payload, es_payload, inserts = [], [], []
    for el in de_elems:
        fields = OrderedDict((k, el[k]) for k in ("header", "subheader", "bodytext") if el.get(k))
        translated = {}
        if fields:
            attempts = 0
            while attempts < 2:
                attempts += 1
                try:
                    translated = translate_fields(fields, guide, model, gate_feedback=gate_feedback)
                    break
                except Exception as e:
                    log(f"  pid {pid} uid {el['uid']}: Modell/Parse-Fehler ({e}) Versuch {attempts}")
                    translated = {}
        final = {k: (translated[k] if (translated and k in translated) else (el.get(k) or ""))
                 for k in ("header", "subheader", "bodytext")}
        final["bodytext"] = localize_blog_meta(final["bodytext"], el.get("bodytext", "") or "", lang)
        de_payload.append({"de_uid": el["uid"], "bodytext": el.get("bodytext", "") or ""})
        es_payload.append({"de_uid": el["uid"], "bodytext": final["bodytext"],
                           "CType": el["CType"], "sorting": el["sorting"]})
        donor = find_donor(pid, el["colPos"], el["sorting"]) or el      # Mirror#5: DE-Quelle als Donor
        inserts.append((donor, el["uid"], final))
    return de_payload, es_payload, inserts

def process_page(pid, lang, guide, model, dry_run, review_dir, force, log):
    de_ce, es_ce = content_counts(pid, lang)
    if de_ce > 0 and de_ce == es_ce and not force:
        log(f"pid {pid}: vollstaendig ({es_ce}/{de_ce}) -> skip"); return "skip"

    # Fall B (Blog): pages-Overlay fehlt -> erst anlegen; im Dry-Run nur planen (Slug ausgeben).
    ov_status, ov_stmt = ensure_page_overlay(pid, lang, guide, model, dry_run, review_dir, log)
    if ov_status == "blocked":
        log(f"pid {pid}: ABBRUCH — pages-Overlay konnte nicht vorbereitet werden (siehe oben)"); return "blocked"

    de_elems = fetch_de_elements(pid)
    if not de_elems:
        log(f"pid {pid}: keine DE-Elemente -> skip"); return "skip"

    taglines = []
    # Pass 1: uebersetzen + gaten.
    de_payload, es_payload, inserts = translate_page(de_elems, guide, model, pid, lang, log)
    ok, gout = run_gates(de_payload, es_payload, taglines)
    if not ok:
        # Gate-Feedback-Retry — exakt 1x, auf SEITEN-Ebene, mit LESBAREM Feedback (humanisiert, nicht roh).
        fb = humanize_gate_feedback(gout, de_payload, es_payload)
        log(f"pid {pid}: GATES FAIL (Pass 1) -> Retry mit lesbarem Feedback:\n{fb}")
        de_payload, es_payload, inserts = translate_page(de_elems, guide, model, pid, lang, log, gate_feedback=fb)
        ok, gout = run_gates(de_payload, es_payload, taglines)
        log(f"pid {pid}: GATES {'gruen' if ok else 'FAIL'} nach Retry (Pass 2)")

    if dry_run:
        # IMMER schreiben — auch bei FAIL, damit Grenzfaelle reviewbar sind.
        # ALLE uebersetzten Felder persistieren (header/subheader/bodytext je Element) fuer --from-review.
        os.makedirs(review_dir, exist_ok=True)
        p = os.path.join(review_dir, f"{LANG_ISO.get(lang, lang)}-{pid}.json")
        de_by_uid = {el["uid"]: el for el in de_elems}
        rich = [{"de_uid": de_uid, "CType": de_by_uid[de_uid]["CType"], "sorting": de_by_uid[de_uid]["sorting"],
                 "header": final["header"], "subheader": final["subheader"], "bodytext": final["bodytext"]}
                for (_donor, de_uid, final) in inserts]
        out = {"_gates": "PASS" if ok else "FAIL", "_gout": gout,
               "page_overlay": ov_status, "elements": rich}
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log(f"pid {pid}: Dry-Run -> {p}  gates={'PASS' if ok else 'FAIL'} ({len(rich)} Elemente, page-overlay={ov_status})")
        return "dry_ok" if ok else "dry_gate_fail"

    if not ok:
        log(f"pid {pid}: GATES FAIL (nach Retry) -> geflaggt, KEIN INSERT"); return "gate_fail"

    # Commit: Overlay (falls neu) + Content-INSERTs in EINER Transaktion.
    stmts = []
    if ov_stmt is not None:
        stmts.append(ov_stmt)
    stmts += [build_insert(d, de_uid, lang, tr, pid) for (d, de_uid, tr) in inserts]
    db_execute_tx(stmts)
    log(f"pid {pid}: {len(inserts)} {LANG_ISO.get(lang, lang)}-Content-Overlays + "
        f"{'1 Page-Overlay ' if ov_stmt is not None else ''}inserted (gates gruen, page-overlay={ov_status})")
    return "committed"

def build_page_overlay_from_review(de_pid, lang, page_json, log):
    """Wie ensure_page_overlay, aber Textfelder/Slug aus dem REVIEWten page.json (KEIN Modell-Call).
    nav_hide/doktype kommen frisch aus der DE-Quelle; Donor-Klon frisch aus DB."""
    if page_overlay_exists(de_pid, lang):
        return ("exists", None)
    de_rows = db_query("SELECT * FROM pages WHERE uid=%s AND deleted=0", (de_pid,))
    if not de_rows:
        log(f"  pid {de_pid}: DE-Seite nicht gefunden -> blocked"); return ("blocked", None)
    de = de_rows[0]
    donor_rows = db_query("SELECT * FROM pages WHERE l10n_parent=%s AND sys_language_uid=3 AND deleted=0 LIMIT 1", (de_pid,))
    if not donor_rows:
        log(f"  pid {de_pid}: KEIN RU-pages-Overlay als Vorlage -> blocked"); return ("blocked", None)
    donor = donor_rows[0]
    text_values = {k: (page_json.get(k) if page_json.get(k) is not None else (de.get(k) or "")) for k in PAGE_MIRROR_TEXT}
    slug = page_json.get("slug") or build_page_slug(de.get("slug"), text_values.get("title") or "")
    slug2 = dedupe_slug(slug, lang)
    if slug2 != slug:
        log(f"  pid {de_pid}: WARN Slug-Kollision seit Dry-Run: {slug} -> {slug2}")
    return ("create", _page_overlay_stmt(de, donor, lang, text_values, slug2))

def commit_page_from_review(pid, lang, review_dir, log):
    """--from-review: INSERTs byte-genau aus den reviewten JSONs bauen (kein Modell-Call),
    run_gates als Safety-Gurt, dann Overlay+Content in EINER TX. Fehlt ein JSON -> skip+WARN."""
    iso = LANG_ISO.get(lang, lang)
    cpath = os.path.join(review_dir, f"{iso}-{pid}.json")
    ppath = os.path.join(review_dir, f"{iso}-{pid}.page.json")

    de_ce, es_ce = content_counts(pid, lang)
    if de_ce > 0 and de_ce == es_ce:
        log(f"pid {pid}: vollstaendig ({es_ce}/{de_ce}) -> skip"); return "skip"
    if not os.path.exists(cpath):
        log(f"pid {pid}: WARN Review-JSON fehlt ({cpath}) -> skip (NIE neu uebersetzen)"); return "missing_review"
    review = json.load(open(cpath, encoding="utf-8"))
    if review.get("_gates") != "PASS":
        log(f"pid {pid}: WARN Review-JSON _gates={review.get('_gates')} (nicht PASS) -> skip"); return "missing_review"
    rev_elems = {e["de_uid"]: e for e in review.get("elements", [])}

    # Page-Overlay (falls noch nicht vorhanden) aus page.json
    ov_status, ov_stmt = "exists", None
    if not page_overlay_exists(pid, lang):
        if not os.path.exists(ppath):
            log(f"pid {pid}: WARN page.json fehlt ({ppath}) -> skip"); return "missing_review"
        ov_status, ov_stmt = build_page_overlay_from_review(pid, lang, json.load(open(ppath, encoding="utf-8")), log)
        if ov_status == "blocked":
            log(f"pid {pid}: ABBRUCH page-overlay -> skip"); return "blocked"

    de_elems = fetch_de_elements(pid)
    if not de_elems:
        log(f"pid {pid}: keine DE-Elemente -> skip"); return "skip"
    de_by_uid = {el["uid"]: el for el in de_elems}
    if set(rev_elems) != set(de_by_uid):
        log(f"pid {pid}: WARN Review-Elemente {sorted(rev_elems)} != DE {sorted(de_by_uid)} -> skip"); return "mismatch"

    de_payload, es_payload, inserts = [], [], []
    for el in de_elems:
        rv = rev_elems[el["uid"]]
        final = {k: (rv.get(k) or "") for k in ("header", "subheader", "bodytext")}
        de_payload.append({"de_uid": el["uid"], "bodytext": el.get("bodytext", "") or ""})
        es_payload.append({"de_uid": el["uid"], "bodytext": final["bodytext"], "CType": el["CType"], "sorting": el["sorting"]})
        donor = find_donor(pid, el["colPos"], el["sorting"]) or el
        inserts.append((donor, el["uid"], final))

    ok, gout = run_gates(de_payload, es_payload, [])          # No-Model-Safety-Check
    if not ok:
        log(f"pid {pid}: GATES FAIL (from-review safety) -> KEIN INSERT, skip\n{gout}"); return "gate_fail"

    stmts = []
    if ov_stmt is not None:
        stmts.append(ov_stmt)
    stmts += [build_insert(d, de_uid, lang, tr, pid) for (d, de_uid, tr) in inserts]
    db_execute_tx(stmts)
    log(f"pid {pid}: {len(inserts)} Content + {'1 Page-Overlay ' if ov_stmt is not None else ''}inserted FROM REVIEW "
        f"(gates gruen, page-overlay={ov_status})")
    return "committed"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pids", required=True, help="z. B. 201-389 oder 391,392,45")
    ap.add_argument("--lang", type=int, default=4)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--commit", action="store_true")
    ap.add_argument("--review-dir", default=os.path.expanduser("~/exports/es-review"))
    ap.add_argument("--from-review", metavar="DIR", default=None,
                    help="COMMIT aus reviewten Dry-Run-JSONs (kein Modell-Call); Gates laufen als Safety-Gurt")
    ap.add_argument("--force", action="store_true", help="auch vollstaendige Seiten neu (Vorsicht: Doppel-Insert!)")
    a = ap.parse_args()
    if a.from_review and not a.commit:
        ap.error("--from-review nur zusammen mit --commit")

    _load_secrets()
    guide = open(GUIDE_PATH, encoding="utf-8").read()
    pids = parse_pids(a.pids)
    logp = os.path.expanduser(f"~/exports/rollout_{LANG_ISO.get(a.lang, a.lang)}_{int(time.time())}.log")
    os.makedirs(os.path.dirname(logp), exist_ok=True)
    logf = open(logp, "w", encoding="utf-8")
    def log(m): print(m); logf.write(m + "\n"); logf.flush()

    mode = "dry-run" if a.dry_run else ("COMMIT(from-review)" if a.from_review else "COMMIT")
    log(f"rollout: lang={a.lang} mode={mode} model={a.model} pids={len(pids)}")
    summary = {}
    for pid in pids:
        try:
            if a.from_review:
                r = commit_page_from_review(pid, a.lang, a.from_review, log)
            else:
                r = process_page(pid, a.lang, guide, a.model, a.dry_run, a.review_dir, a.force, log)
        except Exception as e:
            r = "error"; log(f"pid {pid}: EXCEPTION {e}")
        summary[r] = summary.get(r, 0) + 1
    log(f"\n=== Summary: {dict(summary)} ===")
    if UNMAPPED_BLOG_CATS:
        log(f"WARN: NICHT gemappte Blog-Kategorien (an Daniel melden, NICHT raten): {sorted(UNMAPPED_BLOG_CATS)}")
    if a.commit and summary.get("committed"):
        flush_cache(log)

if __name__ == "__main__":
    main()
