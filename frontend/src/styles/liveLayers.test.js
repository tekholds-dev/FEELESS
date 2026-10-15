// ⚡ Agents-tab lag (2026-10-14): the m-live aurora on a page-tall panel was a 2392×7160 rotating GPU layer. Keep it capped + still there.
const fs = require('fs'); const path = require('path');
const css = f => fs.readFileSync(path.join(__dirname, f), 'utf8');

test('m-live aurora layer is capped in height', () => {
  expect(css('meta.css')).toMatch(/\.m-live::before \{[^}]*height: min\(170%, 1200px\)/);
});
test('the Agents tab-wide aurora does not animate or promote a layer', () => {
  const rule = css('agentDesk.css').match(/\.agd\.m-live::before \{([^}]*)\}/);
  expect(rule).toBeTruthy();
  expect(rule[1]).toMatch(/animation: none/);
  expect(rule[1]).toMatch(/will-change: auto/);
  expect(rule[1]).not.toMatch(/translate3d|translateZ|scale3d/);
});
