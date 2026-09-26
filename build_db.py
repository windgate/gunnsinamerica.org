#!/usr/bin/env python3
"""
build_db.py — GEDCOM → public/database/index.html for GunnsinAmerica.org

Builds the self-contained Family Database page from the Ancestry GEDCOM export.

PRIVACY: people who are presumed LIVING are withheld from the published page.
  • They get no card of their own.
  • Where they appear as a parent, spouse, or child on someone else's card,
    they are shown only as "Living" — no name, dates, or places.
  • Marriage dates/places involving a living spouse are dropped.

A person is treated as DECEASED if the GEDCOM has any death, burial,
cremation, or probate record for them (even with no date), or if their
birth year — actual or estimated — is more than LIVING_WINDOW years ago.
Everyone else is presumed living. When nothing at all can be estimated,
the person is presumed living (UNKNOWN_IS_LIVING).

Manual overrides live in database-privacy.json (same folder as this script):
  "force_private": GEDCOM IDs to always withhold (removal requests)
  "force_public":  GEDCOM IDs to always show (living people who consented,
                   or deceased people the GEDCOM lacks a death record for)
IDs are the database card IDs, e.g. "I222104369410" (no @ signs).

Usage:
  python3 build_db.py                       # default GEDCOM path below
  python3 build_db.py path/to/tree.ged      # another GEDCOM
  python3 build_db.py --report              # also list everyone withheld, and why
                                            # (printed to the terminal only — never
                                            #  written into the repo)
"""

import re, sys, json, html
from datetime import date
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
HERE    = Path(__file__).resolve().parent
GEDCOM  = Path("/Users/johnpaull/Desktop/Current Projects/Genealogy/03_Gunn Project/Gunn_line_family_tree.ged")
OUT     = HERE / "public" / "database" / "index.html"
PRIVACY_FILE = HERE / "database-privacy.json"

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
OUT.parent.mkdir(parents=True, exist_ok=True)


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
    return p.replace(", United States", "").replace(", USA", "").strip()

def extract_surname(name):
    name_clean = re.sub(r'"[^"]*"', "", name).strip()
    parts = name_clean.split()
    return parts[-1] if len(parts) > 1 else (parts[0] if parts else "")


# ── Parse GEDCOM ───────────────────────────────────────────────────────────
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
                        cur.update(name="", sex="", birth={}, death={}, deceased=False,
                                   occupation="", famc=[], fams=[], event_years=[])
                    elif cur_type == "FAM":
                        cur.update(husb=None, wife=None, chil=[], marr={})
                else:
                    cur_id = cur_type = None
                continue

            if cur_type == "INDI":
                if level == "1":
                    tag1 = tag
                    if tag == "NAME":                       # last NAME wins (matches original script)
                        cur["name"] = value.replace("/", "").strip()
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


# ── Living / deceased determination ────────────────────────────────────────
def load_overrides():
    if not PRIVACY_FILE.exists():
        return set(), set()
    data = json.loads(PRIVACY_FILE.read_text(encoding="utf-8"))
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

force_private, force_public = load_overrides()
status = classify(individuals, families, force_private, force_public)
is_living = lambda i: status.get(i, (True, ""))[0]

def rel_name(i):
    return LIVING_LABEL if is_living(i) else clean_name(individuals[i]["name"])

people, withheld = [], []
for iid, p in individuals.items():
    raw = p["name"].strip()
    if not raw: continue
    if is_living(iid):
        withheld.append(iid)
        continue
    name    = clean_name(raw)
    surname = extract_surname(name)
    if not surname or surname.startswith('"'):
        surname = name.split()[-1] if name.split() else "Unknown"

    par = []
    for fid in p["famc"]:
        fam = families.get(fid, {})
        for role in ("husb", "wife"):
            q = fam.get(role)
            if q and q in individuals and individuals[q]["name"]:
                par.append(rel_name(q))

    sps, kids = [], []
    for fid in p["fams"]:
        fam = families.get(fid, {})
        for role in ("husb", "wife"):
            s = fam.get(role)
            if s and s != iid and s in individuals and individuals[s]["name"]:
                if is_living(s):
                    sps.append({"name": LIVING_LABEL, "marr_date": "", "marr_place": ""})
                else:
                    m = fam.get("marr") or {}
                    sps.append({"name": rel_name(s), "marr_date": m.get("date", ""),
                                "marr_place": clean_place(m.get("place", ""))})
        for c in fam.get("chil", []):
            if c in individuals and individuals[c]["name"]:
                if is_living(c):
                    kids.append({"name": LIVING_LABEL, "birth_date": ""})
                else:
                    kids.append({"name": rel_name(c),
                                 "birth_date": individuals[c]["birth"].get("date", "")})

    people.append({
        "id": iid.strip("@"), "name": name, "surname": surname, "sex": p["sex"],
        "birth_date": p["birth"].get("date", ""), "birth_place": clean_place(p["birth"].get("place", "")),
        "death_date": p["death"].get("date", ""), "death_place": clean_place(p["death"].get("place", "")),
        "occupation": p["occupation"], "parents": par, "spouses": sps, "children": kids,
    })

people.sort(key=lambda r: (r["surname"].upper(), r["name"].upper()))
surnames = sorted({r["surname"] for r in people
                   if r["surname"] and not r["surname"].startswith('"') and r["surname"] != "%"})

print(f"Published {len(people):,} records · withheld {len(withheld):,} presumed living")
if force_private or force_public:
    print(f"Overrides: {len(force_private)} force_private, {len(force_public)} force_public")

if REPORT:
    print("\nWithheld as living (terminal only — not written anywhere):")
    for i in sorted(withheld, key=lambda i: clean_name(individuals[i]["name"]).upper()):
        print(f"  {i.strip('@'):<16} {clean_name(individuals[i]['name']):<40} {status[i][1]}")


# ── HTML ───────────────────────────────────────────────────────────────────
def jsd(obj): return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Family Database - Gunns in America</title>
<meta name="description" content="Searchable database of the Gunn family line and related families. Details of living people are withheld."/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Raleway:wght@400;600&display=swap" rel="stylesheet"/>
<style>
:root{--ink:#1c1814;--ink-light:#4a3f35;--paper:#f5f0e8;--paper-dark:#e8e0d0;--rule:#c8baa0;--accent:#7a3b1e;--accent2:#3b5c3e;--gold:#b08840;--white:#fdfaf4;--serif:'Playfair Display',Georgia,serif;--body:'Libre Baskerville',Georgia,serif;--sans:'Raleway',sans-serif;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--paper);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.7;}
a{color:inherit;}
.skip{position:absolute;left:1rem;top:-3rem;z-index:1000;padding:.6rem 1rem;background:var(--gold);color:var(--ink);font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;}
.skip:focus{top:.75rem;}
.nav{background:var(--ink);border-bottom:3px solid var(--gold);padding:.9rem 2rem;display:flex;align-items:center;justify-content:space-between;}
.nav-brand{font-family:var(--serif);font-size:1.1rem;color:var(--paper);text-decoration:none;}
.nav-brand span{color:var(--gold);}
.nav-back{font-family:var(--sans);font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--paper-dark);text-decoration:none;}
.nav-back:hover{color:var(--gold);}
.hdr{background:var(--accent);color:var(--paper);padding:2rem;}
.hdr h1{font-family:var(--serif);font-size:clamp(1.5rem,3vw,2.2rem);font-weight:700;margin-bottom:.25rem;}
.hdr p{font-family:var(--sans);font-size:.78rem;opacity:.9;}
.hdr .priv{margin-top:.35rem;}
.hdr .priv a{color:var(--paper);text-underline-offset:2px;}
.ctrl{background:var(--paper-dark);border-bottom:1px solid var(--rule);padding:1rem 2rem;display:flex;gap:1rem;flex-wrap:wrap;align-items:center;position:sticky;top:0;z-index:10;}
.srch{font-family:var(--body);font-size:.9rem;padding:.45rem .9rem;border:1px solid var(--rule);background:var(--white);color:var(--ink);flex:1;min-width:200px;}
.srch:focus,.sel:focus{outline:2px solid var(--accent);outline-offset:1px;}
.sel{font-family:var(--sans);font-size:.75rem;padding:.45rem .7rem;border:1px solid var(--rule);background:var(--white);color:var(--ink);cursor:pointer;}
.cnt{font-family:var(--sans);font-size:.72rem;color:var(--ink-light);margin-left:auto;white-space:nowrap;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1px;background:var(--rule);}
.card{background:var(--white);padding:1.25rem 1.5rem;cursor:pointer;transition:background .15s;border:none;border-top:2px solid transparent;text-align:left;font:inherit;color:inherit;display:block;width:100%;}
.card:hover{background:var(--paper);border-top-color:var(--accent);}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;background:var(--paper);}
.card-name{font-family:var(--serif);font-size:1rem;font-weight:700;margin-bottom:.3rem;line-height:1.3;}
.card-dates{font-family:var(--sans);font-size:.7rem;letter-spacing:.05em;color:var(--accent);margin-bottom:.3rem;}
.card-place{font-size:.78rem;color:var(--ink-light);margin-bottom:.3rem;}
.card-tags{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.4rem;}
.tag{font-family:var(--sans);font-size:.6rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;padding:1px 6px;border:1px solid;}
.tag-s{color:var(--accent2);border-color:var(--accent2);}
.tag-r{color:var(--ink-light);border-color:var(--rule);}
.ov{display:none;position:fixed;inset:0;background:rgba(28,24,20,.88);z-index:100;align-items:center;justify-content:center;padding:1.5rem;}
.ov.open{display:flex;}
.mod{background:var(--white);max-width:640px;width:100%;max-height:90vh;overflow-y:auto;position:relative;}
.mod-hdr{background:var(--ink);color:var(--paper);padding:1.5rem 2.5rem 1.25rem 2rem;border-bottom:3px solid var(--gold);}
.mod-name{font-family:var(--serif);font-size:1.6rem;font-weight:700;line-height:1.2;margin-bottom:.4rem;}
.mod-meta{font-family:var(--sans);font-size:.72rem;letter-spacing:.06em;color:var(--gold);line-height:1.8;}
.mod-body{padding:1.5rem 2rem;display:flex;flex-direction:column;gap:1.25rem;}
.sec{padding-bottom:1.25rem;border-bottom:1px solid var(--rule);}
.sec:last-child{border-bottom:none;padding-bottom:0;}
.lbl{font-family:var(--sans);font-size:.62rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-light);margin-bottom:.4rem;}
.val{font-size:.9rem;color:var(--ink);line-height:1.7;}
.val ul{list-style:none;padding:0;}
.val li{padding:.2rem 0;border-bottom:1px solid var(--paper-dark);}
.val li:last-child{border-bottom:none;}
.val li.lv{color:var(--ink-light);font-style:italic;}
.sub{font-size:.8rem;color:var(--ink-light);margin-left:.5rem;}
.cls{position:absolute;top:1rem;right:1rem;background:none;border:1px solid rgba(245,240,232,.3);color:var(--paper);font-size:1.1rem;width:32px;height:32px;cursor:pointer;display:flex;align-items:center;justify-content:center;}
.cls:hover,.cls:focus-visible{background:var(--accent);border-color:var(--accent);outline:none;}
.empty{grid-column:1/-1;padding:4rem 2rem;text-align:center;color:var(--ink-light);font-style:italic;background:var(--white);}
.ftr{background:var(--ink);color:var(--rule);text-align:center;padding:2rem;border-top:3px solid var(--gold);font-family:var(--sans);font-size:.72rem;letter-spacing:.06em;margin-top:1px;}
.ftr a{color:var(--rule);text-decoration:none;margin:0 .5rem;}
.ftr a:hover{color:var(--gold);}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}
@media(max-width:540px){.grid{grid-template-columns:1fr;}.ctrl{padding:.75rem 1rem;}}
</style>
</head>
<body>
<a class="skip" href="#grid">Skip to records</a>
<nav class="nav" aria-label="Primary">
  <a class="nav-brand" href="/"><span>Gunns</span> in America</a>
  <a class="nav-back" href="/">← Back to Site</a>
</nav>
<header class="hdr">
  <h1>Family Database</h1>
  <p>__N_PEOPLE__ individuals &nbsp;·&nbsp; __N_FAMILIES__ family units &nbsp;·&nbsp; Gunn line and related families</p>
  <p class="priv">Details of living people are withheld. <a href="/privacy">Privacy Policy</a></p>
</header>
<main>
<div class="ctrl" role="search">
  <label class="sr" for="srch">Search records</label>
  <input class="srch" id="srch" type="search" placeholder="Search by name, place, or date…" autocomplete="off" oninput="go()"/>
  <label class="sr" for="sn">Filter by surname</label>
  <select class="sel" id="sn" onchange="go()">
    <option value="">All Surnames</option>
    __SURNAME_OPTIONS__
  </select>
  <label class="sr" for="sx">Filter by sex</label>
  <select class="sel" id="sx" onchange="go()">
    <option value="">All</option>
    <option value="M">Male</option>
    <option value="F">Female</option>
  </select>
  <span class="cnt" id="cnt" role="status" aria-live="polite">__N_PEOPLE__ records</span>
</div>
<div class="grid" id="grid" tabindex="-1"></div>
</main>
<div class="ov" id="ov" onclick="mc(event)">
  <div class="mod" role="dialog" aria-modal="true" aria-labelledby="mn">
    <button class="cls" id="cls" onclick="cl()" aria-label="Close">✕</button>
    <div class="mod-hdr">
      <h2 class="mod-name" id="mn"></h2>
      <div class="mod-meta" id="mm"></div>
    </div>
    <div class="mod-body" id="mb"></div>
  </div>
</div>
<footer class="ftr">Gunns in America &nbsp;·&nbsp; GunnsinAmerica.org &nbsp;·&nbsp; Family Database
  <div style="margin-top:.6rem"><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a><a href="/accessibility">Accessibility</a></div>
</footer>
<script>
const P=__DATA__;
const LV=__LIVING__;
const IX={};P.forEach(p=>IX[p.id]=p);
let F=P.slice(),lastFocus=null;
function e(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
function render(){
  const g=document.getElementById('grid');
  document.getElementById('cnt').textContent=F.length.toLocaleString()+' records';
  if(!F.length){g.innerHTML='<p class="empty">No matching records found.</p>';return;}
  const sh=F.slice(0,500);
  g.innerHTML=sh.map(p=>{
    const dt=[p.birth_date,p.death_date].filter(Boolean).join(' – ');
    const pl=p.birth_place||p.death_place||'';
    const rc=p.parents.length+p.spouses.length+p.children.length;
    return`<button type="button" class="card" onclick="om('${p.id}')"><div class="card-name">${e(p.name)}</div>${dt?`<div class="card-dates">${e(dt)}</div>`:''}<div class="card-place">${e(pl)}</div><div class="card-tags"><span class="tag tag-s">${e(p.surname)}</span>${rc?`<span class="tag tag-r">${rc} relation${rc!==1?'s':''}</span>`:''}</div></button>`;
  }).join('');
  if(F.length>500)g.innerHTML+=`<p class="empty">Showing 500 of ${F.length.toLocaleString()} — refine search to see more.</p>`;
}
function go(){
  const q=document.getElementById('srch').value.toLowerCase();
  const sn=document.getElementById('sn').value.toUpperCase();
  const sx=document.getElementById('sx').value;
  F=P.filter(p=>{
    if(sn&&p.surname.toUpperCase()!==sn)return false;
    if(sx&&p.sex!==sx)return false;
    if(q&&![p.name,p.birth_place,p.death_place,p.birth_date,p.death_date].join(' ').toLowerCase().includes(q))return false;
    return true;
  });
  render();
}
function li(name,extra){return name===LV?`<li class="lv">${e(LV)}</li>`:`<li>${e(name)}${extra||''}</li>`;}
function om(id){
  const p=IX[id];if(!p)return;
  lastFocus=document.activeElement;
  document.getElementById('mn').textContent=p.name;
  const ml=[];
  if(p.sex)ml.push(p.sex==='M'?'Male':'Female');
  if(p.birth_date||p.birth_place)ml.push('Born: '+[p.birth_date,p.birth_place].filter(Boolean).join(', '));
  if(p.death_date||p.death_place)ml.push('Died: '+[p.death_date,p.death_place].filter(Boolean).join(', '));
  if(p.occupation)ml.push('Occupation: '+p.occupation);
  document.getElementById('mm').innerHTML=ml.map(l=>`<div>${e(l)}</div>`).join('');
  let b='';
  if(p.parents.length)b+=`<div class="sec"><h3 class="lbl">Parents</h3><div class="val"><ul>${p.parents.map(n=>li(n)).join('')}</ul></div></div>`;
  if(p.spouses.length)b+=`<div class="sec"><h3 class="lbl">Spouse${p.spouses.length>1?'s':''}</h3><div class="val"><ul>${p.spouses.map(s=>{const d=[s.marr_date,s.marr_place].filter(Boolean).join(', ');return li(s.name,d?`<span class="sub">m. ${e(d)}</span>`:'');}).join('')}</ul></div></div>`;
  if(p.children.length)b+=`<div class="sec"><h3 class="lbl">Children (${p.children.length})</h3><div class="val"><ul>${p.children.map(c=>{const yr=c.birth_date?c.birth_date.split(' ').pop():'';return li(c.name,yr?`<span class="sub">b. ${e(yr)}</span>`:'');}).join('')}</ul></div></div>`;
  if(!b)b='<div class="sec"><p style="color:var(--ink-light);font-style:italic">No family connections recorded in this dataset.</p></div>';
  document.getElementById('mb').innerHTML=b;
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
  document.getElementById('cls').focus();
}
function cl(){
  const ov=document.getElementById('ov');if(!ov.classList.contains('open'))return;
  ov.classList.remove('open');document.body.style.overflow='';
  if(lastFocus)lastFocus.focus();
}
function mc(ev){if(ev.target===document.getElementById('ov'))cl();}
document.addEventListener('keydown',ev=>{
  if(ev.key==='Escape')cl();
  if(ev.key==='Tab'&&document.getElementById('ov').classList.contains('open')){
    const f=[...document.querySelectorAll('.mod button,.mod a')];if(!f.length)return;
    const a=f[0],z=f[f.length-1];
    if(ev.shiftKey&&document.activeElement===a){ev.preventDefault();z.focus();}
    else if(!ev.shiftKey&&document.activeElement===z){ev.preventDefault();a.focus();}
  }
});
render();
</script>
</body>
</html>"""

print("Building HTML...")
page = (TEMPLATE
        .replace("__SURNAME_OPTIONS__", "".join(
            f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in surnames))
        .replace("__N_PEOPLE__", f"{len(people):,}")
        .replace("__N_FAMILIES__", f"{len(families):,}")
        .replace("__LIVING__", jsd(LIVING_LABEL))
        .replace("__DATA__", jsd(people)))

OUT.write_text(page, encoding="utf-8")
print(f"Done! Written to {OUT}")
print(f"Size: {OUT.stat().st_size:,} bytes")
