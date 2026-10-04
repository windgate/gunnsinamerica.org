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

// A relational reference can be a bare slug string (when the
// relationship is well-established and needs no hedge), or an
// object carrying a certainty/relationship note for the
// evidence-first cases this project cares about.
const personRef = z.union([
  z.string(),
  z.object({
    ref:       z.string(),
    certainty: z.enum(['documented', 'probable', 'disputed', 'unproven', 'traditional']).optional(),
    note:      z.string().optional(), // freeform hedge, e.g. "named as mother in family wills"
  }),
]);

const relatedRef = z.union([
  z.string(),
  z.object({
    ref:          z.string(),
    relationship: z.string().optional(), // freeform, e.g. "father-and-medical-predecessor"
  }),
]);

const people = defineCollection({
  type: 'content',
  schema: z.object({
    title:            z.string(),
    epithet:          z.string().optional(),
    birth:            z.string().optional(),
    death:            z.string().optional(),
    birthplace:       z.string().optional(),
    deathplace:       z.string().optional(),
    marriage:         z.string().optional(),
    burial:           z.string().optional(),
    location:         z.string().optional(), // combined/summary location, e.g. "Milford and Derby, Connecticut Colony"
    // Person-specific era enum: adds compound spans (e.g. lives that
    // straddle two periods) that don't apply to single-event articles.
    era:              z.enum(['Colonial', 'Revolutionary', 'Colonial and Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Reform and Civil War', 'Modern']).optional(),
    eraLabel:         z.string().optional(),
    leadImage:        z.string().optional(),
    leadImageAlt:     z.string().optional(),
    leadImageCaption: z.string().optional(),
    featured:         z.boolean().default(false),
    order:            z.number().optional(),
    date:             z.date().optional(),
    summary:          z.string().optional(),
    tags:             z.array(z.string()).optional(),
    sources:          z.array(z.string()).optional(),
    related:          z.array(relatedRef).optional(),
    spouse:           z.array(personRef).optional(),
    parents:          z.array(personRef).optional(),
    children:         z.array(personRef).optional(),
    draft:            z.boolean().default(false),
  }),
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
    type:         z.enum(['memoir', 'diary', 'fiction', 'letter', 'essay', 'poem', 'obituary', 'newspaper', 'other']),
    source:       z.string().optional(),
    sourceUrl:    z.string().optional(),
    rights:       z.enum(['public-domain', 'family-permission', 'rights-pending', 'all-rights-reserved']),
    era:          z.enum(['Colonial', 'Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Modern']),
    lineage:      z.enum(['direct', 'connected']).default('connected'),
    excerpt:      z.string().optional(),
    featured:     z.boolean().default(false),
    audioUrl:     z.string().optional(),
    audioReader:  z.string().optional(),
    pdfUrl:       z.string().optional(),
    editorNote:   z.string().optional(),
  }),
});

// ── photo-collections ────────────────────────────────────
// Curated photo sets for one person, place, or event.
// One file per collection: src/content/photo-collections/<slug>.md
// The frontmatter lists photos by their `image` path exactly as it
// appears in public/gallery-data.json (the single photo registry);
// title, year and caption come from there unless overridden here.
// The Markdown body is an optional short introduction.
// A photo may appear in any number of collections.
const photoCollections = defineCollection({
  type: 'content',
  schema: z.object({
    title:    z.string(),
    kind:     z.enum(['person', 'place', 'event']),
    summary:  z.string().optional(),
    years:    z.string().optional(),   // e.g. "1816–1881" or "1861"
    place:    z.string().optional(),   // e.g. "Washington, Connecticut"
    person:   z.string().optional(),   // people slug — shows this set on that person's page
    article:  z.string().optional(),   // articles slug — links to the related article
    // Image path of the featured photo; defaults to the first photo listed.
    featured: z.string().optional(),
    order:    z.number().optional(),
    draft:    z.boolean().default(false),
    photos: z.array(z.object({
      image:   z.string(),             // must match an `image` in gallery-data.json
      title:   z.string().optional(),  // overrides the registry title
      year:    z.string().optional(),  // overrides the registry year
      caption: z.string().optional(),  // overrides the registry caption
      alt:     z.string().optional(),  // alt text; defaults to the title
    })).min(1),
  }),
});

export const collections = {
  articles,
  people,
  journal,
  voices,
  'photo-collections': photoCollections,
};