import { defineCollection, reference, z } from 'astro:content';


const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title:          z.string(),
    subtitle:       z.string(),
    era:            z.enum(['Colonial', 'Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Modern']),
    eraLabel:       z.string(),
    dateRange:      z.string(),
    keyFigure:      z.string(),
    location:       z.string(),
    date:           z.date(),
    featured:       z.boolean().default(false),
    // ↓ add these four lines anywhere inside this object:
    description:    z.string().optional(),
    author:         z.string().optional(),
    imprint:        z.string().optional(),
    draft:          z.boolean().default(false),
    // ↑
    leadImage:      z.string().optional(),
    leadImageAlt:   z.string().optional(),
    // ... rest of your existing fields stay as they are ...
    sources:        z.array(z.string()).optional(),
  }),
});

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

const people = defineCollection({
  type: 'content',
  schema: z.object({
    title:            z.string(),
    epithet:          z.string().optional(),
    birth:            z.string().optional(),   // string, to preserve "c. 1607", "1670/71"
    death:            z.string().optional(),
    birthplace:       z.string().optional(),
    deathplace:       z.string().optional(),
    era:              z.string().optional(),
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
    related:          z.array(z.string()).optional(),
    parents:          z.array(reference('people')).optional(),
    spouse:           z.array(reference('people')).optional(),
    children:         z.array(reference('people')).optional(),
    draft:            z.boolean().default(false),
  }),
});

const contributions = defineCollection({
  type: 'content',
  schema: z.object({
    title:         z.string().optional(),
    contributor:   z.string(),
    relationship:  z.string().optional(),
    date:          z.date(),
    excerpt:       z.string().optional(),
    relatedPerson: reference('people').optional(),
    featured:      z.boolean().default(false),
    order:         z.number().optional(),
    draft:         z.boolean().default(false),
  }),
});

export const collections = { articles, journal, people, contributions };
