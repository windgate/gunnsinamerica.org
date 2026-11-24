// robots.txt points here. Two child sitemaps keep the 6,000+ database URLs apart from the editorial pages.
export function GET({ site }: { site: URL }) {
  const base = site.toString().replace(/\/$/, '');
  const now = new Date().toISOString().slice(0, 10);
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>${base}/sitemap-pages.xml</loc><lastmod>${now}</lastmod></sitemap>
  <sitemap><loc>${base}/sitemap-database.xml</loc><lastmod>${now}</lastmod></sitemap>
</sitemapindex>
`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
