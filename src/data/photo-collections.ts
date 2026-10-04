// Build-time helpers for photo collections.
//
// public/gallery-data.json stays the one registry of photos (the gallery
// intake tool keeps writing to it). A collection is just a curated,
// ordered list of those photos, so every collection photo is resolved
// against the registry here. A typo in an image path fails the build
// with a message naming the collection and the path, instead of
// publishing a broken thumbnail.

import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { getCollection, type CollectionEntry } from 'astro:content';
import registry from '../../public/gallery-data.json';

type RegistryItem = {
  title:    string;
  era?:     string;
  year?:    string;
  image:    string;
  caption?: string;
  subject?: string;
  type?:    string;
};

export type CollectionPhoto = {
  image:   string;
  title:   string;
  year:    string;
  caption: string;
  alt:     string;
  type:    string;
};

export type ResolvedCollection = {
  entry:    CollectionEntry<'photo-collections'>;
  slug:     string;
  featured: CollectionPhoto;
  photos:   CollectionPhoto[];
};

const byImage = new Map<string, RegistryItem>(
  (registry as RegistryItem[]).map(item => [item.image, item]),
);

export function resolveCollection(
  entry: CollectionEntry<'photo-collections'>,
): ResolvedCollection {
  const d = entry.data;

  const photos: CollectionPhoto[] = d.photos.map(p => {
    const reg = byImage.get(p.image);
    if (!reg) {
      throw new Error(
        `[photo-collections] "${entry.slug}": ${p.image} is not in public/gallery-data.json. ` +
        `Add it through the gallery intake tool first, or fix the path.`,
      );
    }
    if (!existsSync(join(process.cwd(), 'public', p.image))) {
      throw new Error(
        `[photo-collections] "${entry.slug}": ${p.image} is listed in gallery-data.json ` +
        `but the file is not in public/.`,
      );
    }
    const title = p.title ?? reg.title;
    return {
      image:   p.image,
      title,
      year:    p.year    ?? reg.year    ?? '',
      caption: p.caption ?? reg.caption ?? '',
      alt:     p.alt     ?? title,
      type:    reg.type ?? '',
    };
  });

  const featured = d.featured
    ? photos.find(p => p.image === d.featured)
    : photos[0];
  if (!featured) {
    throw new Error(
      `[photo-collections] "${entry.slug}": featured photo ${d.featured} is not listed in its photos.`,
    );
  }

  // Featured photo always leads, then the rest in the order written.
  const ordered = [featured, ...photos.filter(p => p !== featured)];

  return { entry, slug: entry.slug, featured, photos: ordered };
}

export async function getCollections(): Promise<ResolvedCollection[]> {
  const entries = await getCollection('photo-collections', ({ data }) => !data.draft);
  return entries
    .map(resolveCollection)
    .sort((a, b) =>
      (a.entry.data.order ?? 999) - (b.entry.data.order ?? 999) ||
      a.entry.data.title.localeCompare(b.entry.data.title),
    );
}

export async function getCollectionForPerson(
  personSlug: string,
): Promise<ResolvedCollection | undefined> {
  const all = await getCollections();
  return all.find(c => c.entry.data.person === personSlug);
}
