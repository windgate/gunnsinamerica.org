# Photo collections

A collection is a curated, ordered set of photos for one **person**, **place**, or **event**:
one featured photo, then clickable thumbnails. Collections live at `/collections` and
`/collections/<slug>`; a person collection also appears under *Photographs* on that
person's biography page.

## How it fits together

- `public/gallery-data.json` is still the only photo registry. Add photos with the gallery intake tool as before.
- A collection is one Markdown file in `src/content/photo-collections/` that lists photos by their `image` path.
  Title, year, and caption come from the registry unless overridden in the collection.
- A photo can be in any number of collections (e.g. the 1861 camp photo is in both the event and the place).
- The build fails with a clear message if a listed image isn't in `gallery-data.json` or the file is missing from `public/`.
- Everything is rendered at build time. Without JavaScript the thumbnails are plain links to the full images.

## Adding a collection

1. Make sure the photos are in the gallery (intake tool). `git pull` first.
2. Find them: `npm run collection -- search frederick gunnery`
3. Scaffold: 
   ```
   npm run collection -- new frederick-william-gunn \
     --title "Frederick William Gunn" --kind person \
     --person frederick-william-gunn --years "1816–1881" \
     --place "Washington, Connecticut" --match frederick
   ```
   This writes `src/content/photo-collections/frederick-william-gunn.md` as `draft: true`
   with every matching photo listed. `--match` can be repeated.
4. Edit the file: delete photos that don't belong, put them in the order you want, add a one-line `summary`
   and a short introduction below the frontmatter.
5. Remove `draft: true` to publish.

## Frontmatter

```yaml
title: "Frederick William Gunn"
kind: person            # person | place | event
years: "1816–1881"      # optional
place: "Washington, Connecticut"   # optional
person: "frederick-william-gunn"   # optional: people slug; shows the set on that biography
article: "some-article-slug"       # optional: links to an article (omit the line if none)
summary: "One sentence."           # optional
featured: "/images/gallery/people/frederick-w-gunn-c1860.jpg"   # optional; default is the first photo
order: 10               # optional; lower sorts first
draft: false
photos:
  - image: "/images/gallery/people/frederick-w-gunn-c1860.jpg"
  - image: "/images/gallery/documents/fw-gunn-camping-portrait-1860s.jpg"
    caption: "Optional caption that replaces the gallery caption for this collection only."
```

Per-photo overrides: `title`, `year`, `caption`, `alt`.

## Using the viewer elsewhere

```astro
---
import PhotoCollection from '../components/PhotoCollection.astro';
import { getCollections } from '../data/photo-collections';
const set = (await getCollections()).find(c => c.slug === 'the-gunnery-school');
---
<PhotoCollection photos={set.photos} label="Photographs of The Gunnery" />
```

## Viewer behavior

Click a thumbnail, use the arrow buttons, or press ← / → to change the featured photo.
Click the featured photo to enlarge it (Esc closes). Photos are the originals from `public/`;
very large files will slow a collection down, so resize anything over about 500 KB before adding it.
