// 🌫 NO STROBES (owner, 2026-10-21/22: "no strobes" — Familia first, then site-wide): a hard on/off flash (`steps()` timing) is banned in every
// sheet; activity is a slow fade or glow (≤ 0.4 Hz). A real sprite / typewriter that needs steps() goes in ALLOW with its reason.
const fs = require('fs');
const path = require('path');

const ALLOW = new Set([]);
test.each(fs.readdirSync(__dirname).filter(f => f.endsWith('.css')))('%s has no steps() strobe', file => {
  const css = fs.readFileSync(path.join(__dirname, file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const hits = [...css.matchAll(/animation(?:-timing-function)?\s*:[^;}]*steps\(/g)].map(m => m[0].slice(0, 80)).filter(h => !ALLOW.has(`${file}: ${h}`));
  expect(hits).toEqual([]);
});
