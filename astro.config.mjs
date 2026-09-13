import { defineConfig } from 'astro/config';
import rehypeInlineCaptionFigures from './src/plugins/inline-caption-figures.mjs';

export default defineConfig({
  site: 'https://gunnsinamerica.org',
  base: '/',
  output: 'static',
  markdown: {
    rehypePlugins: [rehypeInlineCaptionFigures],
  },
});
