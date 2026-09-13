// src/plugins/inline-caption-figures.mjs
//
// Rehype plugin (build-time only — no runtime/browser dependency).
//
// Scope: files under src/content/people/ only.
//
// Converts this authoring pattern:
//
//   ![alt text](image-url)
//
//   *Caption text.*
//
// into:
//
//   <figure class="inline">
//     <img src="image-url" alt="alt text" />
//     <figcaption>Caption text.</figcaption>
//   </figure>
//
// This matches the `figure.inline` CSS already defined in
// src/pages/people/[slug].astro (float: right; max-width: 240px),
// so bio images automatically render small and right-floated with
// body text wrapping around them — no manual HTML required.
//
// OPT OUT (full-width image instead): write raw HTML directly rather
// than Markdown image syntax. Raw HTML passes through this plugin
// untouched, since it never matches the "plain paragraph containing
// only an <img>, followed by a plain paragraph containing only an
// <em>" pattern this plugin looks for:
//
//   <figure class="full">
//     <img src="image-url" alt="alt text" />
//     <figcaption>Caption text.</figcaption>
//   </figure>
//
// No new npm dependencies — plain recursive traversal of the hast tree.

function onlyMeaningfulChildren(node) {
  return node.children.filter(
    c => !(c.type === 'text' && c.value.trim() === '')
  );
}

function isImageOnlyParagraph(node) {
  if (!node || node.type !== 'element' || node.tagName !== 'p') return false;
  const kids = onlyMeaningfulChildren(node);
  return kids.length === 1 && kids[0].type === 'element' && kids[0].tagName === 'img';
}

function isEmphasisOnlyParagraph(node) {
  if (!node || node.type !== 'element' || node.tagName !== 'p') return false;
  const kids = onlyMeaningfulChildren(node);
  return kids.length === 1 && kids[0].type === 'element' && kids[0].tagName === 'em';
}

export default function rehypeInlineCaptionFigures() {
  return (tree, file) => {
    // file.history[0] is the absolute source path Astro/vfile assigns
    // to the markdown file currently being processed.
    const sourcePath = (file && file.history && file.history[0]) || (file && file.path) || '';
    const normalized = sourcePath.replace(/\\/g, '/');
    if (!normalized.includes('/content/people/')) return;

    const walk = (node) => {
      if (!node.children) return;

      const newChildren = [];
      for (let i = 0; i < node.children.length; i++) {
        const current = node.children[i];
        const next = node.children[i + 1];

        if (isImageOnlyParagraph(current) && isEmphasisOnlyParagraph(next)) {
          const img = onlyMeaningfulChildren(current)[0];
          const em  = onlyMeaningfulChildren(next)[0];

          newChildren.push({
            type: 'element',
            tagName: 'figure',
            properties: { className: ['inline'] },
            children: [
              img,
              {
                type: 'element',
                tagName: 'figcaption',
                properties: {},
                children: em.children,
              },
            ],
          });

          i++; // skip the caption paragraph — already consumed above
          continue;
        }

        newChildren.push(current);
      }

      node.children = newChildren;
      node.children.forEach(walk);
    };

    walk(tree);
  };
}
