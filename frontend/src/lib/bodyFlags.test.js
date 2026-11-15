import { syncBodyFlags } from './bodyFlags';

test('a marker on the page sets its body flag, and leaving clears it', () => {
  const el = document.createElement('div'); el.className = 'fuse-page'; document.body.appendChild(el);
  syncBodyFlags();
  expect(document.body.classList.contains('has-fuse-page')).toBe(true);
  expect(document.body.classList.contains('has-hqp')).toBe(false);
  el.remove(); syncBodyFlags();
  expect(document.body.classList.contains('has-fuse-page')).toBe(false);
});

test('no CSS rule makes the whole page re-check a :has() on every change (use a body flag instead)', () => {
  const fs = require('fs'); const path = require('path');
  const dir = path.join(__dirname, '..', 'styles'); const bad = [];
  fs.readdirSync(dir).filter(f => f.endsWith('.css')).forEach(f => {
    const css = fs.readFileSync(path.join(dir, f), 'utf8');
    // body:has(> .x) (a direct child) and html:has(body.x) are cheap; body:has(.x) / .terminal-app:has(.x) search the whole page
    (css.match(/(?:^|[\s,}])(?:body|:root|\.terminal-app|\.app-shell)[\w.-]*:has\(\s*(?!>)[^)]*\)/g) || []).forEach(m => bad.push(`${f}: ${m.trim()}`));
  });
  expect(bad).toEqual([]);
});
