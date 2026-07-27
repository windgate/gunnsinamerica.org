# Gunns in America — Astro

**gunnsinamerica.org** · Static site hosted on GitHub Pages  
Companion website to the Gunn family history book.

---

## Migration from static HTML

Your existing files map to Astro like this:

| Old file | New location | Notes |
|---|---|---|
| `index.html` | `src/pages/index.astro` | Ported — same content |
| `article-template.html` | `src/pages/articles/[slug].astro` | Template is now the Astro layout |
| `jasper-gunn.html` | `src/content/articles/jasper-gunn-arrives.md` | Content is now Markdown |
| `mary-baldwin.html` | `src/content/articles/mary-baldwin.md` | Add using same frontmatter pattern |
| `articles/index.html` | `src/pages/articles/index.astro` | Ported with era filter |
| `gallery.html` | `src/pages/gallery/index.astro` | Images loaded from `public/gallery-data.json` |
| `gallery/` images | `public/images/gallery/` | Copy your images here |
| `images/` | `public/images/` | Copy entire folder |
| `favicon.ico` | `public/favicon.ico` | Copy as-is |
| Database tool | `public/database/` | Drop in unchanged, served at /database |

---

## Project structure

```
src/
  layouts/
    BaseLayout.astro        ← nav, head, footer (edit once, applies everywhere)
  pages/
    index.astro             ← home page
    articles/
      index.astro           ← article listing with era filter
      [slug].astro          ← individual article (auto-generated from content)
    journal/
      index.astro           ← research journal
    gallery/
      index.astro           ← photo gallery
  content/
    config.ts               ← frontmatter schemas
    articles/               ← one .md file per article
    journal/                ← one .md file per journal entry

public/
  CNAME                     ← custom domain (do not delete)
  favicon.ico
  gallery-data.json         ← add gallery images here as JSON array
  images/
    articles/               ← article images
    gallery/                ← gallery photos
  database/                 ← your existing database tool (unchanged)
```

---

## Adding an article

Create `src/content/articles/your-slug.md`:

```md
---
title: "Your Title"
subtitle: "One sentence description shown in listings and article header."
era: Colonial
eraLabel: "Colonial Era · 1635"
dateRange: "1635 – 1660"
keyFigure: "Person's Name"
location: "Place Name"
date: 2026-07-01
featured: false
people:
  - name: "Person Name"
    role: "Their role in the story"
sources:
  - "Source one with full citation"
  - "Source two"
prevArticle:
  title: "Previous Article Title"
  slug: "previous-article-slug"
nextArticle:
  title: "Next Article Title"
  slug: "next-article-slug"
---

Article body in Markdown. Use ## for section headings.

Inline image (floats right):
<figure class="inline">
  <img src="/images/articles/your-image.jpg" alt="Description" />
  <figcaption>Caption — Source</figcaption>
</figure>

Full-width image:
<figure class="full">
  <img src="/images/articles/your-image.jpg" alt="Description" />
  <figcaption>Caption — Source</figcaption>
</figure>

Pull quote:
> "Quote text here."
> <cite>— Source, Date</cite>
```

---

## Adding a journal entry

Create `src/content/journal/your-entry.md`:

```md
---
title: "What you found or didn't"
historicalYear: "1863"
date: 2026-07-15
tag: Civil War
link:
  text: "Read the full article"
  url: "/articles/your-article"
---

Entry body in Markdown.
```

---

## Adding gallery images

Edit `public/gallery-data.json`:

```json
[
  {
    "title": "Portrait of Thomas Gunn",
    "era": "Civil War",
    "year": "c. 1863",
    "image": "/images/gallery/thomas-gunn.jpg",
    "caption": "Thomas Gunn, 14th Connecticut Infantry, c. 1863"
  }
]
```

---

## Local development

```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # builds to dist/
npm run preview    # preview the build
```

## Deployment

Push to `main` — GitHub Actions builds and deploys automatically.

**First time only:** go to repo **Settings → Pages → Source → GitHub Actions**.
