// CSS hygiene guard: the stylesheet only shrinks. Every class rule must be used by a component, and the legacy
// sheets have a size budget — new surfaces are built from the m-* presets in meta.css instead of new CSS.
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..');
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const code = walk(SRC).filter(f => /\.jsx?$/.test(f) && !/\.test\./.test(f)).map(f => fs.readFileSync(f, 'utf8')).join('\n')
  + walk(path.join(SRC, '..', 'public')).filter(f => f.endsWith('.html')).map(f => fs.readFileSync(f, 'utf8')).join('\n');
const tokens = new Set(code.match(/[A-Za-z_][\w-]*/g));
const dynamic = [...code.matchAll(/([A-Za-z_][\w-]*-)\$\{/g), ...code.matchAll(/['"]([A-Za-z_][\w-]*-)['"]\s*\+/g)].map(m => m[1]);
const used = c => tokens.has(c) || dynamic.some(d => c.startsWith(d));

// KB budgets. Legacy sheets: lower them when you delete CSS, never raise them. meta.css is where new UI lives, so it
// has its own ceiling — keep presets generic so it stays small.
const BUDGET = { 'terminal.css': 540.7, 'command.css': 97.3, 'trade.css': 6.5, 'meta.css': 72 };

test.each(fs.readdirSync(__dirname).filter(f => f.endsWith('.css')))('%s has no dead class rules', file => {
  const css = fs.readFileSync(path.join(__dirname, file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/url\([^)]*\)|\d+\.\d+/g, '');
  const dead = [...new Set([...css.matchAll(/\.([A-Za-z_][\w-]*)/g)].map(m => m[1]))].filter(c => !used(c));
  expect(dead).toEqual([]);
});

test.each(Object.entries(BUDGET))('%s stays under %s KB', (file, kb) => {
  expect(fs.statSync(path.join(__dirname, file)).size / 1024).toBeLessThanOrEqual(kb);
});
