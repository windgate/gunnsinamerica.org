import { getCollection } from 'astro:content';

const fixed = ['/', '/articles/', '/people/', '/voices/', '/gallery/', '/collections/', '/journal/',
  '/contribute/', '/database/', '/database/surnames/', '/book/', '/support/', '/accessibility/', '/privacy/', '/terms/'];

export async function GET({ site }: { site: URL }) {
  const base = site.toString().replace(/\/$/, '');
  const urls = new Set(fixed);
  const add = async (name: string, prefix: string) => {
    for (const e of await getCollection(name as any)) {
      if ((e.data as any).draft) continue;
      urls.add(`${prefix}/${e.slug}/`);
    }
  };
  await add('articles', '/articles');
  await add('people', '/people');
  await add('voices', '/voices');
  await add('photo-collections', '/collections');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${[...urls].sort().map(u => `  <url><loc>${base}${u}</loc></url>`).join('\n')}
</urlset>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
