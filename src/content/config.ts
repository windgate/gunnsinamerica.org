import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title:          z.string(),
    subtitle:       z.string(),
    era:            z.enum(['Colonial', 'Revolutionary', 'War of 1812', 'Frontier', 'Civil War', 'Modern']),
    eraLabel:       z.string(),           // e.g. "Colonial Era · 1635"
    dateRange:      z.string(),           // e.g. "1635 – 1660"
    keyFigure:      z.string(),
    location:       z.string(),
    date:           z.date(),             // publication/sort date
    featured:       z.boolean().default(false),
    leadImage:      z.string().optional(),
    leadImageAlt:   z.string().optional(),
    leadImageCaption: z.string().optional(),
    prevArticle:    z.object({ title: z.string(), slug: z.string() }).optional(),
    nextArticle:    z.object({ title: z.string(), slug: z.string() }).optional(),
    people:         z.array(z.object({
                      name: z.string(),
                      role: z.string(),
                    })).optional(),
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

export const collections = { articles, journal };
