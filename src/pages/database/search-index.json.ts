import { people, lifespan, shortPlace } from '../../data/family-db';

// [id, name, years, birthplace] — fetched on demand by the database search box.
export function GET() {
  const rows = people.map(p => [p.id, p.n, lifespan(p), shortPlace(p.b?.[1])]);
  return new Response(JSON.stringify(rows), { headers: { 'Content-Type': 'application/json' } });
}
