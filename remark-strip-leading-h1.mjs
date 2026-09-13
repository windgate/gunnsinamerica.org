export default function remarkStripLeadingH1() {
  return (tree) => {
    const children = tree.children;

    // 1. Strip a leading H1 (the layout already renders the title)
    if (children[0] && children[0].type === 'heading' && children[0].depth === 1) {
      children.shift();
    }

    // 2. If a thematic break (---) is now first, drop it too
    while (children[0] && children[0].type === 'thematicBreak') {
      children.shift();
    }

    // 3. Collapse any run of consecutive thematic breaks into a single one
    for (let i = children.length - 1; i > 0; i--) {
      if (children[i].type === 'thematicBreak' && children[i - 1].type === 'thematicBreak') {
        children.splice(i, 1);
      }
    }
  };
}