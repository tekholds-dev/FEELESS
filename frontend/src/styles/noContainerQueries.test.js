// 📐 No CSS container queries, anywhere (2026-11-11: three @container boxes made every full style pass on HQ › Sicario's take
// 13–38 s in Chrome; 39 ms with them gone). A box reads its own width with lib/boxRef.js (data-wN + --box-w/--box-h) instead.
// cq units with no container fall back to the viewport, so they are banned too (in sheets and in inline styles).
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..');
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const files = walk(SRC).filter(f => /\.(css|jsx?)$/.test(f) && !/\.test\./.test(f));
const strip = s => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/\s\/\/ .*$/gm, '');

test('no @container, container-type or cq units', () => {
  const bad = [];
  for (const f of files) {
    const t = strip(fs.readFileSync(f, 'utf8'));
    const css = f.endsWith('.css');
    const hits = [...t.matchAll(css ? /@container|container(-type|-name)?\s*:|\d(cq[whib]|cqmin|cqmax)\b/g : /(\d|\})(cq[whib]|cqmin|cqmax)\b|containerType/g)];
    hits.forEach(m => bad.push(`${path.relative(SRC, f)}: ${m[0]}`));
  }
  expect(bad).toEqual([]);
});
