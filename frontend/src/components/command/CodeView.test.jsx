import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CodeLines, MarkJumps, markLines, plainRows } from './CodeView';

test('a part marked on the page is found in the code: gold line, its number, a jump to it', async () => {
  const rows = plainRows('<body>\n  <section class="hero"   id="top">\n    <h1>Hi</h1>\n  </section>\n</body>');
  const hot = markLines(rows, [{ html: '<section class="hero" id="top"><h1>Hi</h1></section>' }, { html: '<p>' }]);   // too short to find: skipped
  expect([...hot.entries()]).toEqual([[1, 1]]);
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><MarkJumps hot={hot} rows={rows} /><CodeLines rows={rows} hot={hot} /></>); });
  expect(el.querySelector('.fcv-l.is-mark').textContent).toContain('class="hero"'); expect(el.querySelector('[data-testid="code-mark-1"]').textContent).toBe('1 · line 2');
  expect(markLines(rows, []).size).toBe(0);
});
