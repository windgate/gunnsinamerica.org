// Presentation helpers for the family database (data comes from build_db.py).
// Living people are never in the data; relatives who are withheld are counts only.
import raw from './family-db.json';
import links from './family-db-links.json';

type Pl = [string, string];
export interface Rec {
  id: string; n: string; s: string; x?: string;
  b?: Pl; d?: Pl; bu?: Pl; bp?: Pl; occ?: string;
  alt?: { n?: string[]; b?: Pl[]; d?: Pl[] };
  par?: string[]; parl?: number; sib?: string[]; sibl?: number;
  sp?: { id: string; d?: string; p?: string }[]; spl?: number;
  ch?: string[]; chl?: number;
  res?: Pl[]; ev?: [string, string, string][];
  src?: number[]; bio?: string; note?: string; core?: number;
}

const data = raw as unknown as {
  generated: string; counts: { people: number; families: number };
  core_line: string[]; sources: string[]; people: Rec[];
};

export const people: Rec[] = data.people;
export const generated = data.generated;
export const counts = data.counts;
export const coreLine: string[] = data.core_line;
export const byId = new Map(people.map(p => [p.id, p]));
export const bioLinks = links as Record<string, string>;

export const slugify = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'unrecorded';

export const yearOf = (d?: string): number | null => {
  const m = (d || '').match(/\b(1\d{3}|20\d{2}|[6-9]\d{2})\b/);
  return m ? +m[1] : null;
};
export const lifespan = (p: Rec) => {
  const b = yearOf(p.b?.[0]), d = yearOf(p.d?.[0]);
  if (b && d) return `${b}–${d}`;
  if (b) return `b. ${b}`;
  if (d) return `d. ${d}`;
  return '';
};
export const sortByBirth = (ids: string[] = []) =>
  ids.map(i => byId.get(i)).filter((p): p is Rec => !!p)
    .sort((a, b) => (yearOf(a.b?.[0]) ?? 9999) - (yearOf(b.b?.[0]) ?? 9999));

export const shortPlace = (pl?: string) => {
  const parts = (pl || '').split(',').map(x => x.trim()).filter(x => x && !/^(america|united states|usa)$/i.test(x));
  if (parts.length <= 2) return parts.join(', ');
  return `${parts[0]}, ${parts[parts.length - 1]}`;
};

// ── Surname groups ─────────────────────────────────────────────────────────
export interface SurnameGroup { slug: string; name: string; people: Rec[] }
const groups = new Map<string, SurnameGroup>();
for (const p of people) {
  const slug = slugify(p.s);
  let g = groups.get(slug);
  if (!g) groups.set(slug, g = { slug, name: p.s, people: [] });
  g.people.push(p);
}
export const surnameGroups = [...groups.values()]
  .sort((a, b) => a.name.localeCompare(b.name, 'en'));
export const surnameBySlug = groups;

// ── Display cleanup ────────────────────────────────────────────────────────
const GENERIC = /^(usa|u\.s\.a?\.?|us|united states(?: of america)?)$/i;
const norm = (s: string) => (s || '').trim().toLowerCase();

export const residences = (p: Rec): Pl[] => {
  const seen = new Set<string>(), out: Pl[] = [];
  for (const [d, pl] of p.res || []) {
    if (!pl || GENERIC.test(pl.trim())) continue;
    const k = norm(d) + '|' + norm(pl);
    if (seen.has(k)) continue;
    seen.add(k); out.push([d, pl]);
  }
  return out.filter(([d, pl]) => d || !out.some(([d2, pl2]) => d2 && norm(pl2).includes(norm(pl)) && norm(pl2) !== norm(pl)));
};
export const events = (p: Rec): [string, string, string][] => {
  const seen = new Set<string>(), out: [string, string, string][] = [];
  for (const e of p.ev || []) {
    const k = e.map(norm).join('|');
    if (seen.has(k)) continue;
    seen.add(k); out.push(e);
  }
  return out;
};
export const sourceTitles = (p: Rec): string[] => {
  const t = (p.src || []).map(i => data.sources[i]).filter(Boolean);
  return [...new Set(t)];
};

// ── Context line (plain text; used for the lede and the meta description) ──
const dp = (x?: Pl) => x && (x[0] || x[1]) ? x : null;
export const contextLine = (p: Rec): string => {
  const born = dp(p.b), died = dp(p.d);
  const phrase = (verb: string, x: Pl) =>
    `${verb} ${[x[0], x[1] && `in ${x[1]}`].filter(Boolean).join(' ')}`;
  const bits = [born && phrase('born', born), died && phrase('died', died)].filter(Boolean) as string[];
  const out: string[] = [];
  if (bits.length) out.push(`${p.n} was ${bits.join('; ')}.`);
  const parents = (p.par || []).map(i => byId.get(i)?.n).filter(Boolean);
  if (parents.length) out.push(`${p.x === 'M' ? 'Son' : p.x === 'F' ? 'Daughter' : 'Child'} of ${parents.slice(0, 2).join(' and ')}.`);
  const sp = (p.sp || []).map(s => ({ s, r: byId.get(s.id) })).filter(x => x.r);
  if (sp.length) out.push(`Married ${sp.map(({ s, r }) => r!.n + (s.d ? ` (${s.d})` : '')).join(', then ')}.`);
  const kids = (p.ch?.length || 0) + (p.chl || 0);
  if (kids) out.push(`${kids} ${kids === 1 ? 'child is' : 'children are'} recorded in the tree.`);
  return out.length ? out.join(' ') : `${p.n} appears in the Gunn family tree; no dates are recorded.`;
};

export const personUrl = (id: string) => `/database/person/${id}/`;
export const surnameUrl = (s: string) => `/database/surname/${slugify(s)}/`;
