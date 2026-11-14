// ↔ PoB SIDE SCROLL (owner 2026-11-13, screenshot): a proof window's main column is a grid; with no column set, its one track grew to the
// widest child (12 sport tabs) and the whole board scrolled sideways. The track must shrink, and the sport strip must scroll inside itself.
const fs = require('fs');
const path = require('path');

const read = f => fs.readFileSync(path.join(__dirname, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const rule = (css, sel) => [...css.matchAll(new RegExp(`(?:^|})\\s*${sel.replace(/[.]/g, '\\.')}\\s*{([^}]*)}`, 'gm'))].map(m => m[1]).join(';');   // every rule for it

test('the proof main column is a grid track that can shrink', () => {
  expect(rule(read('proofKit.css'), '.prf-main')).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
});

test('the sport strip may shrink and scrolls inside its own box', () => {
  const tabs = rule(read('proofTools.css'), '.ptl-tabs');
  expect(tabs).toMatch(/min-width:\s*0/);
  expect(tabs).toMatch(/overflow-x:\s*auto/);
});
