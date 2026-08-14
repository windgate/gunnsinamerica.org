import re, json, html
from pathlib import Path

GEDCOM = Path("/Users/johnpaull/Desktop/Current Projects/Genealogy/03_Gunn Project/Gunn_line_family_tree.ged")
OUT    = Path("/Users/johnpaull/Documents/GitHub/gunnsinamerica.org/public/database/index.html")
OUT.parent.mkdir(parents=True, exist_ok=True)

def parse_gedcom(path):
    individuals, families = {}, {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    current_id = current_type = None
    current = {}
    current_tag = None
    def save():
        if current_id and current_type == "INDI":
            individuals[current_id] = dict(current)
        elif current_id and current_type == "FAM":
            families[current_id] = dict(current)
    for line in lines:
        line = line.rstrip()
        parts = line.split(" ", 2)
        if len(parts) < 2: continue
        level = parts[0]
        rest = parts[1:]
        if level == "0":
            save()
            current = {}
            current_tag = None
            tag = rest[0] if rest else ""
            if tag.startswith("@") and len(rest) > 1:
                current_id = tag
                current_type = rest[1]
            else:
                current_id = current_type = None
        elif level == "1":
            tag = rest[0]
            value = rest[1] if len(rest) > 1 else ""
            current_tag = tag
            if tag == "NAME":  current["name"] = value.replace("/","").strip()
            elif tag == "SEX":  current["sex"] = value
            elif tag == "BIRT": current.setdefault("birth", {})
            elif tag == "DEAT": current.setdefault("death", {})
            elif tag == "OCCU": current["occupation"] = value
            elif tag == "FAMC": current.setdefault("famc",[]).append(value if value.startswith("@") else f"@{value}@")
            elif tag == "FAMS": current.setdefault("fams",[]).append(value if value.startswith("@") else f"@{value}@")
        elif level == "2":
            tag = rest[0]
            value = rest[1] if len(rest) > 1 else ""
            if current_tag == "BIRT":
                if tag == "DATE": current.setdefault("birth",{})["date"] = value
                elif tag == "PLAC": current.setdefault("birth",{})["place"] = value
            elif current_tag == "DEAT":
                if tag == "DATE": current.setdefault("death",{})["date"] = value
                elif tag == "PLAC": current.setdefault("death",{})["place"] = value
        if current_type == "FAM" and level == "1":
            tag = rest[0]
            raw = rest[1] if len(rest) > 1 else ""
            value = raw if raw.startswith("@") else f"@{raw}@"
            if tag == "HUSB":   current["husb"] = value
            elif tag == "WIFE": current["wife"] = value
            elif tag == "CHIL": current.setdefault("chil",[]).append(value)
            elif tag == "MARR": current.setdefault("marr",{})
        if current_type == "FAM" and level == "2":
            tag = rest[0]
            value = rest[1] if len(rest) > 1 else ""
            if "marr" in current:
                if tag == "DATE": current["marr"]["date"] = value
                elif tag == "PLAC": current["marr"]["place"] = value.replace(", United States","").replace(", USA","")
    save()
    return individuals, families

def clean_name(n):
    n = re.sub(r'\s*\(\d+\)\s*$','',n)
    return re.sub(r'\s+',' ',n).strip()

def clean_place(p):
    if not p: return ""
    return p.replace(", United States","").replace(", USA","").strip()

def extract_surname(name):
    name_clean = re.sub(r'"[^"]*"','',name).strip()
    parts = name_clean.split()
    return parts[-1] if len(parts)>1 else (parts[0] if parts else "")

print("Parsing GEDCOM...")
individuals, families = parse_gedcom(GEDCOM)
print(f"Parsed {len(individuals)} individuals, {len(families)} families")

people = []
for iid, p in individuals.items():
    raw = p.get("name","").strip()
    if not raw: continue
    name    = clean_name(raw)
    surname = extract_surname(name)
    if not surname or surname.startswith('"'): surname = name.split()[-1] if name.split() else "Unknown"
    birth = p.get("birth",{})
    death = p.get("death",{})
    parents = []
    for fid in p.get("famc",[]):
        fam = families.get(fid,{})
        for role in ["husb","wife"]:
            pid = fam.get(role)
            if pid and pid in individuals:
                pn = clean_name(individuals[pid].get("name",""))
                if pn: parents.append(pn)
    spouses = []
    for fid in p.get("fams",[]):
        fam = families.get(fid,{})
        for role in ["husb","wife"]:
            sid = fam.get(role)
            if sid and sid != iid and sid in individuals:
                sn = clean_name(individuals[sid].get("name",""))
                marr = fam.get("marr") or {}
                if sn:
                    spouses.append({"name":sn,"marr_date":marr.get("date",""),"marr_place":clean_place(marr.get("place",""))})
    children = []
    for fid in p.get("fams",[]):
        fam = families.get(fid,{})
        for cid in fam.get("chil",[]):
            if cid in individuals:
                cn = clean_name(individuals[cid].get("name",""))
                cb = individuals[cid].get("birth",{})
                if cn: children.append({"name":cn,"birth_date":cb.get("date","") if cb else ""})
    people.append({"id":iid.strip("@"),"name":name,"surname":surname,"sex":p.get("sex",""),"birth_date":birth.get("date",""),"birth_place":clean_place(birth.get("place","")),"death_date":death.get("date",""),"death_place":clean_place(death.get("place","")),"occupation":p.get("occupation",""),"parents":parents,"spouses":spouses,"children":children})

people.sort(key=lambda p:(p["surname"].upper(),p["name"].upper()))
surnames = sorted(set(p["surname"] for p in people if p["surname"] and not p["surname"].startswith('"') and p["surname"] != "%"))
print(f"Built {len(people)} records")

def jsd(obj): return json.dumps(obj,ensure_ascii=False,separators=(',',':'))

page = open("/dev/stdin").read() if False else ""

# Write minimal valid page to test
test = f"People: {len(people)}, Families: {len(families)}"
print(test)

# Now write the full page
import urllib.request
print("Building HTML...")

html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Family Database - Gunns in America</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Raleway:wght@400;600&display=swap" rel="stylesheet"/>
<style>
:root{{--ink:#1c1814;--ink-light:#4a3f35;--paper:#f5f0e8;--paper-dark:#e8e0d0;--rule:#c8baa0;--accent:#7a3b1e;--accent2:#3b5c3e;--gold:#b08840;--white:#fdfaf4;--serif:'Playfair Display',Georgia,serif;--body:'Libre Baskerville',Georgia,serif;--sans:'Raleway',sans-serif;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--paper);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.7;}}
.nav{{background:var(--ink);border-bottom:3px solid var(--gold);padding:.9rem 2rem;display:flex;align-items:center;justify-content:space-between;}}
.nav-brand{{font-family:var(--serif);font-size:1.1rem;color:var(--paper);text-decoration:none;}}
.nav-brand span{{color:var(--gold);}}
.nav-back{{font-family:var(--sans);font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--paper-dark);text-decoration:none;}}
.nav-back:hover{{color:var(--gold);}}
.hdr{{background:var(--accent);color:var(--paper);padding:2rem;}}
.hdr h1{{font-family:var(--serif);font-size:clamp(1.5rem,3vw,2.2rem);font-weight:700;margin-bottom:.25rem;}}
.hdr p{{font-family:var(--sans);font-size:.78rem;opacity:.8;}}
.ctrl{{background:var(--paper-dark);border-bottom:1px solid var(--rule);padding:1rem 2rem;display:flex;gap:1rem;flex-wrap:wrap;align-items:center;position:sticky;top:0;z-index:10;}}
.srch{{font-family:var(--body);font-size:.9rem;padding:.45rem .9rem;border:1px solid var(--rule);background:var(--white);color:var(--ink);flex:1;min-width:200px;outline:none;}}
.srch:focus{{border-color:var(--accent);}}
.sel{{font-family:var(--sans);font-size:.75rem;padding:.45rem .7rem;border:1px solid var(--rule);background:var(--white);color:var(--ink);cursor:pointer;}}
.cnt{{font-family:var(--sans);font-size:.72rem;color:var(--ink-light);margin-left:auto;white-space:nowrap;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1px;background:var(--rule);}}
.card{{background:var(--white);padding:1.25rem 1.5rem;cursor:pointer;transition:background .15s;border-top:2px solid transparent;}}
.card:hover{{background:var(--paper);border-top-color:var(--accent);}}
.card-name{{font-family:var(--serif);font-size:1rem;font-weight:700;margin-bottom:.3rem;line-height:1.3;}}
.card-dates{{font-family:var(--sans);font-size:.7rem;letter-spacing:.05em;color:var(--accent);margin-bottom:.3rem;}}
.card-place{{font-size:.78rem;color:var(--ink-light);margin-bottom:.3rem;}}
.card-tags{{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.4rem;}}
.tag{{font-family:var(--sans);font-size:.6rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;padding:1px 6px;border:1px solid;}}
.tag-s{{color:var(--accent2);border-color:var(--accent2);}}
.tag-r{{color:var(--ink-light);border-color:var(--rule);}}
.ov{{display:none;position:fixed;inset:0;background:rgba(28,24,20,.88);z-index:100;align-items:center;justify-content:center;padding:1.5rem;}}
.ov.open{{display:flex;}}
.mod{{background:var(--white);max-width:640px;width:100%;max-height:90vh;overflow-y:auto;position:relative;}}
.mod-hdr{{background:var(--ink);color:var(--paper);padding:1.5rem 2.5rem 1.25rem 2rem;border-bottom:3px solid var(--gold);}}
.mod-name{{font-family:var(--serif);font-size:1.6rem;font-weight:700;line-height:1.2;margin-bottom:.4rem;}}
.mod-meta{{font-family:var(--sans);font-size:.72rem;letter-spacing:.06em;color:var(--gold);line-height:1.8;}}
.mod-body{{padding:1.5rem 2rem;display:flex;flex-direction:column;gap:1.25rem;}}
.sec{{padding-bottom:1.25rem;border-bottom:1px solid var(--rule);}}
.sec:last-child{{border-bottom:none;padding-bottom:0;}}
.lbl{{font-family:var(--sans);font-size:.62rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-light);margin-bottom:.4rem;}}
.val{{font-size:.9rem;color:var(--ink);line-height:1.7;}}
.val ul{{list-style:none;padding:0;}}
.val li{{padding:.2rem 0;border-bottom:1px solid var(--paper-dark);}}
.val li:last-child{{border-bottom:none;}}
.sub{{font-size:.8rem;color:var(--ink-light);margin-left:.5rem;}}
.cls{{position:absolute;top:1rem;right:1rem;background:none;border:1px solid rgba(245,240,232,.3);color:var(--paper);font-size:1.1rem;width:32px;height:32px;cursor:pointer;display:flex;align-items:center;justify-content:center;}}
.cls:hover{{background:var(--accent);border-color:var(--accent);}}
.empty{{grid-column:1/-1;padding:4rem 2rem;text-align:center;color:var(--ink-light);font-style:italic;}}
.ftr{{background:var(--ink);color:var(--rule);text-align:center;padding:2rem;border-top:3px solid var(--gold);font-family:var(--sans);font-size:.72rem;letter-spacing:.06em;margin-top:1px;}}
@media(max-width:540px){{.grid{{grid-template-columns:1fr;}}.ctrl{{padding:.75rem 1rem;}}}}
</style>
</head>
<body>
<nav class="nav">
  <a class="nav-brand" href="/"><span>Gunns</span> in America</a>
  <a class="nav-back" href="/">← Back to Site</a>
</nav>
<div class="hdr">
  <h1>Family Database</h1>
  <p>{len(people):,} individuals &nbsp;·&nbsp; {len(families):,} family units &nbsp;·&nbsp; Gunn line and related families</p>
</div>
<div class="ctrl">
  <input class="srch" id="srch" type="search" placeholder="Search by name, place, or date…" autocomplete="off" oninput="go()"/>
  <select class="sel" id="sn" onchange="go()">
    <option value="">All Surnames</option>
    {''.join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in surnames)}
  </select>
  <select class="sel" id="sx" onchange="go()">
    <option value="">All</option>
    <option value="M">Male</option>
    <option value="F">Female</option>
  </select>
  <span class="cnt" id="cnt">{len(people):,} records</span>
</div>
<div class="grid" id="grid"></div>
<div class="ov" id="ov" onclick="mc(event)">
  <div class="mod">
    <button class="cls" onclick="cl()">✕</button>
    <div class="mod-hdr">
      <div class="mod-name" id="mn"></div>
      <div class="mod-meta" id="mm"></div>
    </div>
    <div class="mod-body" id="mb"></div>
  </div>
</div>
<footer class="ftr">Gunns in America &nbsp;·&nbsp; GunnsinAmerica.org &nbsp;·&nbsp; Family Database</footer>
<script>
const P={jsd(people)};
const IX={{}};P.forEach(p=>IX[p.id]=p);
let F=P.slice();
function e(s){{const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}}
function render(){{
  const g=document.getElementById('grid');
  document.getElementById('cnt').textContent=F.length.toLocaleString()+' records';
  if(!F.length){{g.innerHTML='<p class="empty">No matching records found.</p>';return;}}
  const sh=F.slice(0,500);
  g.innerHTML=sh.map(p=>{{
    const dt=[p.birth_date,p.death_date].filter(Boolean).join(' \u2013 ');
    const pl=p.birth_place||p.death_place||'';
    const rc=p.parents.length+p.spouses.length+p.children.length;
    return`<div class="card" onclick="om('${{p.id}}')"><div class="card-name">${{e(p.name)}}</div>${{dt?`<div class="card-dates">${{e(dt)}}</div>`:''}}<div class="card-place">${{e(pl)}}</div><div class="card-tags"><span class="tag tag-s">${{e(p.surname)}}</span>${{rc?`<span class="tag tag-r">${{rc}} relation${{rc!==1?'s':''}}</span>`:''}}</div></div>`;
  }}).join('');
  if(F.length>500)g.innerHTML+=`<p class="empty">Showing 500 of ${{F.length.toLocaleString()}} \u2014 refine search to see more.</p>`;
}}
function go(){{
  const q=document.getElementById('srch').value.toLowerCase();
  const sn=document.getElementById('sn').value.toUpperCase();
  const sx=document.getElementById('sx').value;
  F=P.filter(p=>{{
    if(sn&&p.surname.toUpperCase()!==sn)return false;
    if(sx&&p.sex!==sx)return false;
    if(q&&![p.name,p.birth_place,p.death_place,p.birth_date,p.death_date].join(' ').toLowerCase().includes(q))return false;
    return true;
  }});
  render();
}}
function om(id){{
  const p=IX[id];if(!p)return;
  document.getElementById('mn').textContent=p.name;
  const ml=[];
  if(p.sex)ml.push(p.sex==='M'?'Male':'Female');
  if(p.birth_date||p.birth_place)ml.push('Born: '+[p.birth_date,p.birth_place].filter(Boolean).join(', '));
  if(p.death_date||p.death_place)ml.push('Died: '+[p.death_date,p.death_place].filter(Boolean).join(', '));
  if(p.occupation)ml.push('Occupation: '+p.occupation);
  document.getElementById('mm').innerHTML=ml.map(l=>`<div>${{e(l)}}</div>`).join('');
  let b='';
  if(p.parents.length)b+=`<div class="sec"><div class="lbl">Parents</div><div class="val"><ul>${{p.parents.map(n=>`<li>${{e(n)}}</li>`).join('')}}</ul></div></div>`;
  if(p.spouses.length)b+=`<div class="sec"><div class="lbl">Spouse${{p.spouses.length>1?'s':''}}</div><div class="val"><ul>${{p.spouses.map(s=>{{const d=[s.marr_date,s.marr_place].filter(Boolean).join(', ');return`<li>${{e(s.name)}}${{d?`<span class="sub">m. ${{e(d)}}</span>`:''}}`;}}). join('')}}</ul></div></div>`;
  if(p.children.length)b+=`<div class="sec"><div class="lbl">Children (${{p.children.length}})</div><div class="val"><ul>${{p.children.map(c=>{{const yr=c.birth_date?c.birth_date.split(' ').pop():'';return`<li>${{e(c.name)}}${{yr?`<span class="sub">b. ${{e(yr)}}</span>`:''}}`;}}). join('')}}</ul></div></div>`;
  if(!b)b='<div class="sec"><p style="color:var(--ink-light);font-style:italic">No family connections recorded in this dataset.</p></div>';
  document.getElementById('mb').innerHTML=b;
  document.getElementById('ov').classList.add('open');
  document.body.style.overflow='hidden';
}}
function cl(){{document.getElementById('ov').classList.remove('open');document.body.style.overflow='';}}
function mc(ev){{if(ev.target===document.getElementById('ov'))cl();}}
document.addEventListener('keydown',ev=>{{if(ev.key==='Escape')cl();}});
render();
</script>
</body>
</html>"""

OUT.write_text(html_page, encoding="utf-8")
print(f"Done! Written to {OUT}")
print(f"Size: {OUT.stat().st_size:,} bytes")
