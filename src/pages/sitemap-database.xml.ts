import { people, surnameGroups, generated } from '../data/family-db';

export function GET({ site }: { site: URL }) {
  const base = site.toString().replace(/\/$/, '');
  const u = (path: string) => `  <url><loc>${base}${path}</loc><lastmod>${generated}</lastmod></url>`;
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${[...surnameGroups.map(g => u(`/database/surname/${g.slug}/`)), ...people.map(p => u(`/database/person/${p.id}/`))].join('\n')}
</urlset>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
