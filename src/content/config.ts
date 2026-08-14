import { defineCollection, z } from 'astro:content';

// ── Shared schema fields ─────────────────────────────────
// Both articles and people share the same frontmatter shape.
// Defined once here to avoid duplication.

const articleSchema = z.object({
  title:            z.string(),
  subtitle:         z.string(),
  era:              z.enum(['Colonial', 'Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Modern']),
  eraLabel:         z.string(),           // e.g. "Colonial Era · 1635"
  dateRange:        z.string(),           // e.g. "1635 – 1660"
  keyFigure:        z.string(),
  location:         z.string(),
  date:             z.date(),             // publication/sort date
  featured:         z.boolean().default(false),
  leadImage:        z.string().optional(),
  leadImageAlt:     z.string().optional(),
  leadImageCaption: z.string().optional(),
  people: z.array(z.object({
    name: z.string(),
    role: z.string(),
  })).optional(),
  sources:          z.array(z.string()).optional(),
  prevArticle: z.object({
    title: z.string(),
    slug:  z.string(),
  }).optional(),
  nextArticle: z.object({
    title: z.string(),
    slug:  z.string(),
  }).optional(),
});

// ── articles ─────────────────────────────────────────────
// Topic-driven pieces: events, eras, places, themes.
// e.g. colonial-medicine.md, voyage-of-the-defence.md,
//      founding-milford-seven-pillars.md
const articles = defineCollection({
  type:   'content',
  schema: articleSchema,
});

// ── people ───────────────────────────────────────────────
// Biographical articles: one person, one file.
// Slug naming convention: firstname-lastname-birthyear
// e.g. nathaniel-gunn-1637.md, samuel-baldwin-gunn-1642.md
// Exceptions (no year): jasper-gunn.md, christian-gunn.md
const people = defineCollection({
  type:   'content',
  schema: articleSchema,
});

// ── journal ──────────────────────────────────────────────
// Researcher's working diary. First person, dated to when
// written, not when the historical event occurred.
const journal = defineCollection({
  type: 'content',
  schema: z.object({
    title:          z.string(),
    historicalYear: z.string(),
    date:           z.date(),
    tag:            z.string().optional(),
    link: z.object({
      text: z.string(),
      url:  z.string(),
    }).optional(),
  }),
});
// ── voices ───────────────────────────────────────────────
// Primary sources in family members' own words.
// Memoirs, diaries, letters, published fiction, essays.
const voices = defineCollection({
  type: 'content',
  schema: z.object({
    title:        z.string(),
    author:       z.string(),
    authorSlug:   z.string().optional(),
    date:         z.date(),
    composed:     z.string().optional(),
    type:         z.enum(['memoir', 'diary', 'fiction', 'letter', 'essay', 'poem', 'other']),
    source:       z.string().optional(),
    sourceUrl:    z.string().optional(),
    rights:       z.enum(['public-domain', 'family-permission', 'rights-pending', 'all-rights-reserved']),
    era:          z.enum(['Colonial', 'Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Modern']),
    excerpt:      z.string().optional(),
    featured:     z.boolean().default(false),
    audioUrl:     z.string().optional(),
    audioReader:  z.string().optional(),
    pdfUrl:       z.string().optional(),
    editorNote:   z.string().optional(),
  }),
});

export const collections = { articles, people, journal, voices };

