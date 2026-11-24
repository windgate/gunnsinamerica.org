#!/usr/bin/env python3
"""
build_db.py — GEDCOM → src/data/family-db.json for GunnsinAmerica.org

Reads the Ancestry GEDCOM export and writes the cleaned, privacy-filtered data
that the Astro site renders into the Family Database (a page for every person,
a list for every surname, and the search page).

  src/data/family-db.json         every public person's record
  src/data/family-db-links.json   {biography slug: record id}, for the "family record" link
                                  on each biography page

PRIVACY: people who are presumed LIVING are withheld entirely.
  • They get no record of their own.
  • Where they appear as a parent, sibling, spouse, or child on someone else's
    record they are counted only ("Living") — no name, dates, places, or link.
  • Marriage dates/places involving a living spouse are dropped.
  • Free-text notes are never published (they can name living relatives);
    only dates, places, and source TITLES are carried over from the tree.

A person is treated as DECEASED if the GEDCOM has any death, burial,
cremation, or probate record for them (even with no date), or if their
birth year — actual or estimated — is more than LIVING_WINDOW years ago.
Everyone else is presumed living. When nothing at all can be estimated,
the person is presumed living (UNKNOWN_IS_LIVING).

Manual overrides
  database-privacy.json    force_private / force_public lists of record ids
  database-overrides.json  display overrides, the direct-line starting point, and
                           manual biography links (see that file's _readme)

Usage:
  python3 build_db.py                       # default GEDCOM path below
  python3 build_db.py path/to/tree.ged      # another GEDCOM
  python3 build_db.py --report              # also list everyone withheld, and why
                                            # (printed to the terminal only — never
                                            #  written into the repo)
"""

import re, sys, json
from collections import Counter
from datetime import date
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
HERE    = Path(__file__).resolve().parent
GEDCOM  = Path("/Users/johnpaull/Desktop/Current Projects/Genealogy/03_Gunn Project/Gunn_line_family_tree.ged")
DATA_DIR       = HERE / "src" / "data"
OUT_DB         = DATA_DIR / "family-db.json"
OUT_LINKS      = DATA_DIR / "family-db-links.json"
BIO_DIR        = HERE / "src" / "content" / "people"
PRIVACY_FILE   = HERE / "database-privacy.json"
OVERRIDES_FILE = HERE / "database-overrides.json"
OLD_PAGE       = HERE / "public" / "database" / "index.html"

CURRENT_YEAR      = date.today().year
LIVING_WINDOW     = 100    # born within this many years, with no death record → presumed living
UNKNOWN_IS_LIVING = True   # no dates anywhere near this person → presumed living
LIVING_LABEL      = "Living"

# Rough generational offsets used to estimate a missing birth year
AGE_AT_MARRIAGE   = 20     # birth ≈ marriage year − 20
AGE_AT_CHILDBIRTH = 25     # birth ≈ child's birth − 25 ; child ≈ parent + 25
AGE_AT_EVENT      = 30     # birth ≈ latest residence/other event − 30

DEATH_TAGS = {"DEAT", "BURI", "CREM", "PROB"}

args   = [a for a in sys.argv[1:] if not a.startswith("--")]
REPORT = "--report" in sys.argv
if args:
    GEDCOM = Path(args[0]).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────
YEAR_RE = re.compile(r"\b(1[0-9]\d\d|20\d\d)\b")

def years_in(s):
    return [int(y) for y in YEAR_RE.findall(s or "")]

def first_year(s):
    ys = years_in(s)
    return ys[0] if ys else None

def xref(v):
    v = (v or "").strip()
    return v if v.startswith("@") else f"@{v}@"

def clean_name(n):
    n = re.sub(r"\s*\(\d+\)\s*$", "", n or "")
    return re.sub(r"\s+", " ", n).strip()

def clean_place(p):
    if not p: return ""
    p = re.sub(r",(?=\S)", ", ", p)                       # "Connecticut,Colony" → "Connecticut, Colony"
    p = re.sub(r",\s*Colony\b", " Colony", p)             # …→ "Connecticut Colony"
    p = re.sub(r",\s*United States of America\s*$", "", p)
    p = re.sub(r",\s*(?:United States|USA)\s*$", "", p)
    p = re.sub(r"\s+of America\s*$", "", p)
    return re.sub(r"\s+", " ", p).strip(" ,")

def clean_date(d):
    """Dates like 12/24/1943 are ambiguous (month/day order) — keep the year only."""
    d = (d or "").strip()
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", d):
        return d[-4:]
    return d

def extract_surname(name):
    name_clean = re.sub(r'"[^"]*"', "", name).strip()
    parts = name_clean.split()
    return parts[-1] if len(parts) > 1 else (parts[0] if parts else "")

def surname_from_raw(raw):
    """Surname = the text between the slashes in the GEDCOM NAME line.
    Drops parenthetical alternate spellings, Sr/Jr/II/III/IV suffixes and stray
    punctuation, and turns ALL-CAPS into Title Case."""
    m = re.search(r"/([^/]*)/", raw or "")
    if not m:
        return ""
    s = re.sub(r"\([^)]*\)?", "", m.group(1))
    s = re.sub(r"\b(Sr|Jr|II|III|IV)\b\.?", "", s, flags=re.I)
    # Cut at the first marker: alt-spelling slash/backslash, % * ?, " - note", a period, or a symbol/flag
    s = re.split(r"[\\/%*?]|\s-\s|\.(?:\s|$)|\s[^\w\s'’-]", s)[0]
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    if s.isupper() and len(s) > 3:
        s = s.title()
    return s


# ── Name cleanup ───────────────────────────────────────────────────────────
# Ancestry/tree markers that are not part of anyone's name: % * ? + , #1 / (1) / (#2)
# sequence numbers, trailing numbers (Gunn 82), relationship codes (10th GGF, 13GGM,
# 2nd Cousin 1X), research notes like (1m1693 Sarah Clark), and flag emoji with a state
# code. Military ranks (1st Lt.), suffixes (Jr, III), nicknames and (alt spellings) stay.
_FLAGS     = "\U0001F1E6-\U0001F1FF\U0001F3F4\U000E0020-\U000E007F️"
_FLAG_RE   = re.compile(r"\s*[" + _FLAGS + r"]+(?:\s+[A-Z]{2}\b)?")
_SEQ_RE    = re.compile(r"\s*\(\s*#?\d+\s*\)|\s*#\d+")
_GEN_RE    = re.compile(r"\s*\(?\s*\d+\s*(?:st|nd|rd|th)?\s*(?:GGF|GGM)\s*\)?", re.I)
_COUSIN_RE = re.compile(r"\s*\b\d+(?:st|nd|rd|th)\s+Cousin\b(?:\s*\d*X)?", re.I)
_NOTE_RE   = re.compile(r"\s*\(\s*\d*m\d{4}[^)]*\)")
_JUNK_RE   = re.compile(r"[%*?+]")
_TRAIL_NUM = re.compile(r"\s+\d{1,3}\s*$")

def _strip_markers(t):
    t = _JUNK_RE.sub("", _NOTE_RE.sub("", _COUSIN_RE.sub("", _GEN_RE.sub("", _SEQ_RE.sub("", t)))))
    return t

def tidy_name(raw):
    """Return (display_name, surname_text) from a GEDCOM NAME value like 'Mary /Carver */'."""
    s = _FLAG_RE.sub("", raw or "")
    m = re.match(r"^(.*?)/([^/]*)/(.*)$", s, re.S)
    pre, inner, post = m.groups() if m else (s, "", "")
    pre   = _strip_markers(pre).replace("\\", "/")
    post  = _TRAIL_NUM.sub("", _strip_markers(post)).replace("\\", "/")
    inner = _strip_markers(inner)
    parts = [x.strip(" ,.-") for x in inner.split("\\") if x.strip(" ,.-")]
    inner = parts[0] if parts else ""
    if len(parts) > 1:                                  # Winter\Wynter -> Winter (Wynter)
        inner += " (" + " / ".join(parts[1:]) + ")"
    inner = inner.strip(" ,.-")
    if inner.isupper() and len(inner) > 3: inner = inner.title()
    pre = re.sub(r"\b[A-Z]{3,}\b", lambda m: m.group(0).title(), pre.strip())   # NANCY ANN -> Nancy Ann
    post = re.sub(r"\s+\)", ")", post)                                          # "Rodgers )" -> "Rodgers)"
    pre  = re.sub(r"\s+\)", ")", pre)
    if re.search(r"\b(Jr|Sr|II|III|IV)\b\.?\s*$", inner, re.I) and re.match(r"\s*(Jr|Sr|II|III|IV)\b", post, re.I):
        inner = re.sub(r"\s*\b(Jr|Sr|II|III|IV)\b\.?\s*$", "", inner, flags=re.I)  # Baldwin Jr + Jr -> Jr once
    display = re.sub(r"\s+", " ", f"{pre} {inner} {post}").strip(" -")
    return display, inner


# ── Parse GEDCOM (names, vitals, families — drives the living/deceased test) ─
def parse_gedcom(path):
    individuals, families = {}, {}
    cur_id = cur_type = None
    cur = {}
    tag1 = None                       # current level-1 tag

    def save():
        if cur_id and cur_type == "INDI":
            individuals[cur_id] = cur
        elif cur_id and cur_type == "FAM":
            families[cur_id] = cur

    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.rstrip()
            parts = line.split(" ", 2)
            if len(parts) < 2: continue
            level, tag = parts[0], parts[1]
            value = parts[2] if len(parts) > 2 else ""

            if level == "0":
                save()
                cur, tag1 = {}, None
                if tag.startswith("@") and value:
                    cur_id, cur_type = tag, value.strip()
                    if cur_type == "INDI":
                        cur.update(name="", name_raw="", sex="", birth={}, death={}, deceased=False,
                                   occupation="", famc=[], fams=[], event_years=[])
                    elif cur_type == "FAM":
                        cur.update(husb=None, wife=None, chil=[], marr={})
                else:
                    cur_id = cur_type = None
                continue

            if cur_type == "INDI":
                if level == "1":
                    tag1 = tag
                    if tag == "NAME":                       # last non-empty NAME wins (blank NAME lines are ignored)
                        nm, nr = tidy_name(value)
                        if nm: cur["name"], cur["name_raw"] = nm, nr   # markers removed; name_raw = surname text
                    elif tag == "SEX":  cur["sex"] = value.strip()
                    elif tag == "OCCU": cur["occupation"] = value.strip()
                    elif tag == "FAMC": cur["famc"].append(xref(value))
                    elif tag == "FAMS": cur["fams"].append(xref(value))
                    if tag in DEATH_TAGS:
                        cur["deceased"] = True
                elif level == "2":
                    # last BIRT/DEAT value wins (matches original script)
                    if tag1 == "BIRT":
                        if tag == "DATE":   cur["birth"]["date"] = value
                        elif tag == "PLAC": cur["birth"]["place"] = value
                    elif tag1 == "DEAT":
                        if tag == "DATE":   cur["death"]["date"] = value
                        elif tag == "PLAC": cur["death"]["place"] = value
                    elif tag == "DATE" and tag1 in ("RESI", "EVEN", "BAPM", "CHR", "EDUC",
                                                    "_MILT", "FACT", "OCCU", "CENS"):
                        cur["event_years"] += [(tag1, y) for y in years_in(value)]

            elif cur_type == "FAM":
                if level == "1":
                    tag1 = tag
                    if tag == "HUSB":   cur["husb"] = xref(value)
                    elif tag == "WIFE": cur["wife"] = xref(value)
                    elif tag == "CHIL": cur["chil"].append(xref(value))
                elif level == "2" and tag1 == "MARR":
                    # last MARR value wins (matches original script); DIV and other
                    # family events no longer overwrite the marriage date/place
                    if tag == "DATE":   cur["marr"]["date"] = value
                    elif tag == "PLAC": cur["marr"]["place"] = value
    save()
    return individuals, families


# ── Parse GEDCOM again as a tree (burial, residences, events, sources) ─────
LINE_RE = re.compile(r"^(\d+)\s+(?:(@[^@]+@)\s+)?(\S+)(?:\s(.*))?$")

class Node:
    __slots__ = ("tag", "val", "kids", "xref")
    def __init__(self, tag, val="", xref=None):
        self.tag, self.val, self.kids, self.xref = tag, val, [], xref
    def all(self, tag):
        return [k for k in self.kids if k.tag == tag]
    def get(self, tag):
        for k in self.kids:
            if k.tag == tag:
                return k.val.strip()
        return ""
    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()

def parse_tree(path):
    recs, stack = [], []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            m = LINE_RE.match(line.rstrip("\r\n"))
            if not m:
                continue
            lvl, xr, tag, val = int(m.group(1)), m.group(2), m.group(3), (m.group(4) or "")
            if lvl == 0:
                n = Node(tag, val.strip(), xr)
                recs.append(n)
                stack = [n]
                continue
            if not stack or lvl > len(stack):
                continue                                   # malformed line
            if tag in ("CONT", "CONC"):
                par = stack[lvl - 1]
                par.val += ("\n" if tag == "CONT" else "") + val
                continue
            del stack[lvl:]
            node = Node(tag, val)
            stack[lvl - 1].kids.append(node)
            stack.append(node)
    return recs

SKIP_SOURCE_TITLE = re.compile(r"ancestry family tree|public member trees?", re.I)
EVENT_LABELS = {"PROB": "Probate", "WILL": "Will", "NATU": "Naturalization", "IMMI": "Immigration",
                "EMIG": "Emigration", "_MILT": "Military service"}
EVEN_TYPES   = {"Arrival": "Arrival", "Departure": "Departure"}

def last_nonempty(nodes, tag):
    v = ""
    for n in nodes:
        t = n.get(tag)
        if t:
            v = t
    return v

def extract_rich(node, titles, source_index):
    """Everything on a record beyond the basics. Only dates, places and source titles —
    never free-text notes."""
    out = {}
    # alternate birth / death records (the tree often holds several)
    for tag, key in (("BIRT", "b"), ("DEAT", "d")):
        nodes = node.all(tag)
        prim = (last_nonempty(nodes, "DATE"), clean_place(last_nonempty(nodes, "PLAC")))
        alts, seen = [], {(prim[0].casefold(), prim[1].casefold())}
        for n in nodes:
            pair = (n.get("DATE"), clean_place(n.get("PLAC")))
            k = (pair[0].casefold(), pair[1].casefold())
            if (pair[0] or pair[1]) and k not in seen:
                seen.add(k)
                alts.append(pair)
        if alts:
            out.setdefault("alt", {})[key] = [list(a) for a in alts[:4]]
    # burial, baptism
    bu = node.all("BURI")
    if bu and (last_nonempty(bu, "DATE") or last_nonempty(bu, "PLAC")):
        out["bu"] = [clean_date(last_nonempty(bu, "DATE")), clean_place(last_nonempty(bu, "PLAC"))]
    bp = node.all("BAPM") + node.all("CHR")
    if bp and (last_nonempty(bp, "DATE") or last_nonempty(bp, "PLAC")):
        out["bp"] = [clean_date(last_nonempty(bp, "DATE")), clean_place(last_nonempty(bp, "PLAC"))]
    # occupation (the tree's own field; census text is not mined)
    occ = []
    for n in node.all("OCCU"):
        v = re.sub(r"\s+", " ", n.val).strip()
        if v and v.lower() not in {o.lower() for o in occ}:
            occ.append(v)
    if occ:
        out["occ"] = "; ".join(occ)
    # residences
    res, seen = [], set()
    for n in node.all("RESI"):
        d, p = clean_date(n.get("DATE")), clean_place(n.get("PLAC"))
        if (d or p) and (d, p) not in seen:
            seen.add((d, p)); res.append((first_year(d) or 9999, [d, p]))
    if res:
        out["res"] = [r for _, r in sorted(res, key=lambda x: x[0])][:15]
    # selected life events (type, date, place) — no notes
    ev, seen = [], set()
    for n in node.kids:
        label = EVENT_LABELS.get(n.tag)
        if n.tag == "EVEN":
            label = EVEN_TYPES.get(n.get("TYPE"))
        if not label:
            continue
        d, p = clean_date(n.get("DATE")), clean_place(n.get("PLAC"))
        if (d or p) and (label, d, p) not in seen:
            seen.add((label, d, p)); ev.append([label, d, p])
    if ev:
        out["ev"] = ev[:12]
    # source titles (any depth), minus other users' trees
    src, seen = [], set()
    for n in node.walk():
        if n.tag == "SOUR" and n.val.startswith("@"):
            t = titles.get(n.val.strip())
            if not t or SKIP_SOURCE_TITLE.search(t) or t.casefold() in seen:
                continue
            seen.add(t.casefold())
            src.append(source_index.setdefault(t, len(source_index)))
    if src:
        out["src"] = src
    # other recorded names
    return out

def other_names(node, primary):
    names, seen = [], {primary.casefold()}
    for n in node.all("NAME"):
        disp = tidy_name(n.val)[0]
        if disp and disp.casefold() not in seen:
            seen.add(disp.casefold()); names.append(disp)
    return names[:4]


# ── Living / deceased determination ────────────────────────────────────────
def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def load_overrides():
    data = load_json(PRIVACY_FILE, {})
    norm = lambda ids: {str(i).strip().strip("@") for i in ids or []}
    return norm(data.get("force_private")), norm(data.get("force_public"))

def classify(individuals, families, force_private, force_public):
    """Return {indi_id: (is_living, reason)}."""
    cutoff = CURRENT_YEAR - LIVING_WINDOW

    # Known birth years
    birth = {i: first_year(p["birth"].get("date")) for i, p in individuals.items()}
    for i, p in individuals.items():
        if birth[i] is None:
            bap = [y for t, y in p["event_years"] if t in ("BAPM", "CHR")]
            if bap: birth[i] = min(bap)

    # Relationship maps
    parents, children, spouses, marr_years = {}, {}, {}, {}
    for fam in families.values():
        cp = [x for x in (fam["husb"], fam["wife"]) if x in individuals]
        my = first_year(fam["marr"].get("date"))
        for a in cp:
            for b in cp:
                if a != b: spouses.setdefault(a, set()).add(b)
            if my: marr_years.setdefault(a, []).append(my)
            for c in fam["chil"]:
                if c in individuals:
                    children.setdefault(a, set()).add(c)
                    parents.setdefault(c, set()).add(a)

    # Estimate missing birth years by propagating through relatives.
    # The LATEST estimate wins — the conservative choice for privacy.
    est = dict(birth)
    for _ in range(6):
        changed = False
        for i, p in individuals.items():
            if birth[i] is not None: continue
            cands = [y - AGE_AT_MARRIAGE for y in marr_years.get(i, [])]
            cands += [est[c] - AGE_AT_CHILDBIRTH for c in children.get(i, ()) if est.get(c)]
            cands += [est[q] + AGE_AT_CHILDBIRTH for q in parents.get(i, ()) if est.get(q)]
            cands += [est[s] for s in spouses.get(i, ()) if est.get(s)]
            ev = [y for t, y in p["event_years"]]
            if ev: cands.append(max(ev) - AGE_AT_EVENT)
            if cands:
                new = max(cands)
                if est.get(i) != new:
                    est[i], changed = new, True
        if not changed: break

    result = {}
    for i, p in individuals.items():
        pid = i.strip("@")
        if pid in force_private:        result[i] = (True,  "withheld by request (force_private)")
        elif pid in force_public:       result[i] = (False, "shown by override (force_public)")
        elif p["deceased"]:             result[i] = (False, "death/burial record")
        elif birth[i] is not None:
            result[i] = (birth[i] > cutoff, f"born {birth[i]}")
        elif est.get(i) is not None:
            result[i] = (est[i] > cutoff, f"estimated birth ~{est[i]} from relatives/events")
        else:
            result[i] = (UNKNOWN_IS_LIVING, "no dates on person or relatives")
    return result


# ── Build records ──────────────────────────────────────────────────────────
print(f"Parsing GEDCOM: {GEDCOM}")
individuals, families = parse_gedcom(GEDCOM)
print(f"Parsed {len(individuals):,} individuals, {len(families):,} families")
tree = parse_tree(GEDCOM)
titles = {r.xref: r.get("TITL") for r in tree if r.tag == "SOUR" and r.xref and r.get("TITL")}
rich_nodes = {r.xref: r for r in tree if r.tag == "INDI"}
del tree

force_private, force_public = load_overrides()
status = classify(individuals, families, force_private, force_public)
is_living = lambda i: status.get(i, (True, ""))[0]
has_name  = lambda i: i in individuals and bool(individuals[i]["name"].strip())
rid       = lambda i: i.strip("@")
byear     = lambda i: first_year(individuals[i]["birth"].get("date"))

def split_refs(ids):
    """Public ids in order, plus a count of living people (never named)."""
    pubs, living, seen = [], 0, set()
    for i in ids:
        if i in seen or not has_name(i):
            continue
        seen.add(i)
        if is_living(i): living += 1
        else: pubs.append(i)
    return pubs, living

source_index = {}
people, withheld = [], []
for iid, p in individuals.items():
    raw = p["name"].strip()
    if not raw: continue
    if is_living(iid):
        withheld.append(iid)
        continue
    name    = clean_name(raw)
    surname = surname_from_raw("/" + p.get("name_raw", "") + "/")
    if not surname or surname.startswith('"'):
        surname = "Unrecorded"          # no surname in the tree (e.g. just "Abigail"); don't file the first name as a surname

    rec = {"id": rid(iid), "n": name, "s": surname}
    if p["sex"] in ("M", "F"): rec["x"] = p["sex"]
    bd, bpl = p["birth"].get("date", ""), clean_place(p["birth"].get("place", ""))
    dd, dpl = p["death"].get("date", ""), clean_place(p["death"].get("place", ""))
    if bd or bpl: rec["b"] = [bd, bpl]
    if dd or dpl: rec["d"] = [dd, dpl]
    if p["occupation"]: rec["occ"] = p["occupation"]

    # parents, siblings
    par_ids, sib_ids = [], []
    for fid in p["famc"]:
        fam = families.get(fid, {})
        par_ids += [fam.get("husb"), fam.get("wife")]
        sib_ids += [c for c in fam.get("chil", []) if c != iid]
    par, parl = split_refs([x for x in par_ids if x])
    sib, sibl = split_refs(sib_ids)
    sib.sort(key=lambda i: byear(i) or 9999)
    if par:  rec["par"]  = [rid(i) for i in par]
    if parl: rec["parl"] = parl
    if sib:  rec["sib"]  = [rid(i) for i in sib]
    if sibl: rec["sibl"] = sibl

    # spouses (with marriage details) and children
    sp, spl, kid_ids = [], 0, []
    for fid in p["fams"]:
        fam = families.get(fid, {})
        other = fam.get("wife") if fam.get("husb") == iid else fam.get("husb")
        if other and other != iid and has_name(other):
            if is_living(other):
                spl += 1                                    # marriage details dropped
            else:
                m = fam.get("marr") or {}
                e = {"id": rid(other)}
                if m.get("date"):  e["d"] = m["date"]
                if m.get("place"): e["p"] = clean_place(m["place"])
                sp.append(e)
        kid_ids += fam.get("chil", [])
    ch, chl = split_refs(kid_ids)
    ch.sort(key=lambda i: byear(i) or 9999)
    if sp:  rec["sp"]  = sp
    if spl: rec["spl"] = spl
    if ch:  rec["ch"]  = [rid(i) for i in ch]
    if chl: rec["chl"] = chl

    # rich details from the tree
    node = rich_nodes.get(iid)
    if node is not None:
        r = extract_rich(node, titles, source_index)
        if "occ" in r and "occ" in rec: r.pop("occ")
        rec.update(r)
        an = other_names(node, name)
        if an:
            rec.setdefault("alt", {})["n"] = an
    people.append(rec)

# unify surname case variants (Mccord / McCord) to the most common spelling
_canon = {}
for _s, _c in Counter(r["s"] for r in people).most_common():
    _canon.setdefault(_s.casefold(), _s)
for r in people:
    r["s"] = _canon[r["s"].casefold()]

# ── Overrides: display fixes ───────────────────────────────────────────────
OV = load_json(OVERRIDES_FILE, {})
by_id = {r["id"]: r for r in people}
for oid, ov in (OV.get("people") or {}).items():
    r = by_id.get(oid.strip("@"))
    if not r:
        print(f"  ! overrides: no public record {oid}")
        continue
    if ov.get("name"):    r["n"] = ov["name"]
    if ov.get("surname"): r["s"] = ov["surname"]
    if ov.get("note"):    r["note"] = ov["note"]
    if ov.get("birth"):                      # [date] or [date, place]; the tree's original birth moves to "other birth dates"
        old = r.get("b")
        if old and old[0] and old[0] != ov["birth"][0]:
            r.setdefault("alt", {}).setdefault("b", []).insert(0, list(old))
        r["b"] = [ov["birth"][0], (ov["birth"][1] if len(ov["birth"]) > 1 else (old[1] if old else ""))]

# ── Direct line (father to father, from the start person back to the immigrant) ─
core_line = []
start = OV.get("core_line_start")
if start:
    cur = xref(start)
    chain = []
    def father(i):
        hs = []
        for fid in individuals[i]["famc"]:
            h = families.get(fid, {}).get("husb")
            if h and h in individuals and has_name(h) and not is_living(h):
                hs.append(h)
        mine = surname_from_raw("/" + individuals[i].get("name_raw", "") + "/").lower()
        same = [h for h in hs if surname_from_raw("/" + individuals[h].get("name_raw", "") + "/").lower() == mine]
        return (same or hs or [None])[0]       # prefer the father who carries the same surname
    while cur and cur in individuals and len(chain) < 40:
        chain.append(cur)
        cur = father(cur)
    chain.reverse()
    root = xref(OV["core_line_root"]) if OV.get("core_line_root") else ""
    if root and root in chain:
        chain = chain[chain.index(root):]       # start at the immigrant; earlier tree ancestry is not shown as the "line"
    core_line = [rid(i) for i in chain]
    for n, i in enumerate(core_line, 1):
        if i in by_id:
            by_id[i]["core"] = n
    print(f"\nDirect line from the starting person ({len(core_line)} generations, root first):")
    for n, i in enumerate(core_line, 1):
        r = by_id[i]
        print(f"  {n}. {r['n']}  ({(r.get('b') or ['',''])[0]} – {(r.get('d') or ['',''])[0]})  {i}")

# ── Biography links ────────────────────────────────────────────────────────
TITLE_WORDS = {"capt", "captain", "lt", "lieut", "lieutenant", "col", "colonel", "dr", "rev", "deacon",
               "sir", "lady", "gen", "general", "esq", "hon", "sgt", "maj", "major", "mrs", "mr",
               "jr", "sr", "ii", "iii", "iv"}

def name_tokens(s):
    s = re.sub(r"\([^)]*\)", " ", (s or "").lower())
    s = re.sub(r"[“”\"'’.,]", " ", s)
    return {t for t in re.split(r"[\s\-]+", s) if t and t not in TITLE_WORDS}

def frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fm = m.group(1) if m else ""
    def field(k):
        mm = re.search(rf"^{k}:\s*[\"']?(.*?)[\"']?\s*$", fm, re.M)
        return mm.group(1) if mm else ""
    return field("title"), field("birth")

bio_links, bio_report = {}, []
manual = OV.get("bio_links") or {}
if BIO_DIR.exists():
    for f in sorted(BIO_DIR.glob("*.md")):
        slug = f.stem
        title, birth = frontmatter(f)
        if slug in manual:
            if manual[slug]:
                bio_links[slug] = manual[slug].strip("@")
                bio_report.append(f"  {slug:<42} manual → {bio_links[slug]}")
            else:
                bio_report.append(f"  {slug:<42} manual: no link")
            continue
        by = first_year(birth)
        bt = name_tokens(title)
        cands = []
        if by is not None and bt:
            for r in people:
                y = first_year((r.get("b") or ["", ""])[0])
                if y is None or y != by:      # exact birth year only; near misses go to the report
                    continue
                pt = name_tokens(r["n"])
                if len(pt) >= 2 and (bt <= pt or pt <= bt):
                    cands.append((len(bt & pt) / len(bt | pt), r))
        cands.sort(key=lambda x: -x[0])
        if len(cands) == 1 or (len(cands) > 1 and cands[0][0] > cands[1][0]):
            bio_links[slug] = cands[0][1]["id"]
            bio_report.append(f"  {slug:<42} auto   → {cands[0][1]['id']}  {cands[0][1]['n']} ({(cands[0][1].get('b') or [''])[0]})")
        elif cands:
            bio_report.append(f"  {slug:<42} AMBIGUOUS: " + "; ".join(f"{r['id']} {r['n']} ({(r.get('b') or [''])[0]})" for _, r in cands[:4]))
        else:
            bio_report.append(f"  {slug:<42} NO MATCH for “{title}” ({birth or 'no birth year'})")
for slug, i in bio_links.items():
    if i in by_id:
        by_id[i]["bio"] = slug
    else:
        print(f"  ! biography {slug}: record {i} is not public")
print(f"\nBiography links ({len(bio_links)} of {len(bio_report)}):")
print("\n".join(bio_report))

# ── Write ──────────────────────────────────────────────────────────────────
people.sort(key=lambda r: (r["s"].upper(), r["n"].upper(), first_year((r.get("b") or [""])[0]) or 9999))
sources = [t for t, _ in sorted(source_index.items(), key=lambda kv: kv[1])]
out = {
    "generated": date.today().isoformat(),
    "counts": {"people": len(people), "families": len(families)},
    "core_line": core_line,
    "sources": sources,
    "people": people,
}
OUT_DB.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
OUT_LINKS.write_text(json.dumps(dict(sorted(bio_links.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# privacy self-check: nothing withheld may appear anywhere in the output
wid = {rid(i) for i in withheld}
blob_ids = {r["id"] for r in people}
leak = wid & blob_ids
refs = {x for r in people for k in ("par", "sib", "ch") for x in r.get(k, [])} | {s["id"] for r in people for s in r.get("sp", [])}
leak |= (wid & refs)
bad_refs = refs - blob_ids
assert not leak, f"PRIVACY CHECK FAILED: {len(leak)} withheld ids in output"
assert not bad_refs, f"{len(bad_refs)} relative links point to people not in the output"
assert all(re.fullmatch(r"[A-Za-z0-9_-]+", r["id"]) for r in people), "record id with unsafe characters"

print(f"\nPublished {len(people):,} records · withheld {len(withheld):,} presumed living")
print(f"Wrote {OUT_DB.relative_to(HERE)}  ({OUT_DB.stat().st_size/1e6:.1f} MB)  and  {OUT_LINKS.relative_to(HERE)}")
print("Privacy check passed: no withheld person appears in the output.")
if force_private or force_public:
    print(f"Overrides: {len(force_private)} force_private, {len(force_public)} force_public")
if OLD_PAGE.exists():
    print(f"\n! {OLD_PAGE.relative_to(HERE)} still exists. It now conflicts with src/pages/database/index.astro — remove it.")

if REPORT:
    print("\nWithheld as living (terminal only — not written anywhere):")
    for i in sorted(withheld, key=lambda i: clean_name(individuals[i]["name"]).upper()):
        print(f"  {i.strip('@'):<16} {clean_name(individuals[i]['name']):<40} {status[i][1]}")
