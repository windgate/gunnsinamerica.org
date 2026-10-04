#!/usr/bin/env node
// Helper for photo collections. No dependencies.
//
//   npm run collection -- search frederick gunnery
//       List gallery photos whose title, caption or subject contains ANY of the words.
//
//   npm run collection -- new frederick-william-gunn \
//       --title "Frederick William Gunn" --kind person \
//       --person frederick-william-gunn --years "1816–1881" \
//       --place "Washington, Connecticut" --match frederick
//       Writes src/content/photo-collections/<slug>.md with every matching photo
//       listed (title and year as YAML comments). Delete the lines you don't want,
//       reorder the rest, and set `featured:` if the first photo isn't the lead.
//
// Photos always come from public/gallery-data.json; add new ones with the
// gallery intake tool first.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const registry = JSON.parse(readFileSync(join(root, 'public/gallery-data.json'), 'utf8'));

const [cmd, ...rest] = process.argv.slice(2);

function matches(words) {
  const w = words.map(x => x.toLowerCase());
  return registry.filter(it => {
    const hay = `${it.title} ${it.caption ?? ''} ${it.subject ?? ''}`.toLowerCase();
    return w.some(x => hay.includes(x));
  });
}

function flags(args) {
  const out = { _: [], match: [] };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = args[++i];
      if (val === undefined) die(`--${key} needs a value`);
      if (key === 'match') out.match.push(val); else out[key] = val;
    } else out._.push(a);
  }
  return out;
}

function die(msg) { console.error(msg); process.exit(1); }
const q = s => JSON.stringify(s); // YAML-safe double-quoted string

if (cmd === 'search') {
  if (rest.length === 0) die('Usage: npm run collection -- search <word> [word...]');
  const found = matches(rest);
  if (found.length === 0) die('No gallery photos match.');
  for (const it of found) console.log(`${it.image}\n    ${it.title}${it.year ? ` (${it.year})` : ''}\n`);
  console.log(`${found.length} photo${found.length === 1 ? '' : 's'}.`);

} else if (cmd === 'new') {
  const f = flags(rest);
  const slug = f._[0];
  if (!slug || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(slug)) die('Give a lowercase-hyphen slug, e.g. frederick-william-gunn');
  if (!f.title) die('--title is required');
  if (!['person', 'place', 'event'].includes(f.kind)) die('--kind must be person, place, or event');
  const file = join(root, 'src/content/photo-collections', `${slug}.md`);
  if (existsSync(file)) die(`${file} already exists; edit it directly.`);

  const found = f.match.length ? matches(f.match) : [];
  const lines = ['---', `title: ${q(f.title)}`, `kind: ${f.kind}`];
  if (f.years)  lines.push(`years: ${q(f.years)}`);
  if (f.place)  lines.push(`place: ${q(f.place)}`);
  if (f.person) lines.push(`person: ${q(f.person)}`);
  lines.push(`summary: ""`, 'draft: true', 'photos:');
  if (found.length === 0) lines.push('  - image: "/images/gallery/..."');
  for (const it of found) {
    lines.push(`  - image: ${q(it.image)}   # ${it.title}${it.year ? ` (${it.year})` : ''}`);
  }
  lines.push('---', '', 'One or two plain sentences introducing the collection.', '');
  writeFileSync(file, lines.join('\n'));
  console.log(`Wrote ${file}`);
  console.log(`${found.length} photo${found.length === 1 ? '' : 's'} listed. It is saved as draft: true; remove that line when ready to publish.`);

} else {
  die('Commands: search <words...> | new <slug> --title ... --kind person|place|event [--person ...] [--years ...] [--place ...] [--match word]...');
}
