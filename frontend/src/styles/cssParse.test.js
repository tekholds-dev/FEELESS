// Every sheet must parse. Jest never loads CSS, so a stray line (a half-deleted rule) once passed every test and crashed the
// Familia page in the browser (2026-10-21). PostCSS is what the dev server and the build use.
const fs = require('fs');
const path = require('path');
const postcss = require('postcss');

const sheets = fs.readdirSync(__dirname).filter(f => f.endsWith('.css'));
test.each(sheets)('%s parses', f => {
  expect(() => postcss.parse(fs.readFileSync(path.join(__dirname, f), 'utf8'), { from: f })).not.toThrow();
});
