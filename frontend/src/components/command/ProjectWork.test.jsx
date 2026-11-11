import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProjectWork } from './ProjectWork';

const setVal = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
test('its agent changes one file of your repo: price first, the diff, and only Send puts it on its own branch', async () => {
  jest.useFakeTimers(); const calls = [];
  const ask = async b => { calls.push(b); if (b.tools?.dry) return { usd: 0.0031, model: 'x/coder', read: ['src/app.js'] }; if (b.op === 'project_edit') return { draft: 'd1', path: 'src/app.js', added: 1, removed: 1, diff: '--- a/src/app.js\n+++ b/src/app.js\n@@ -1 +1 @@\n-const a = 1;\n+const a = 2;', usd: 0.002 }; return { sent: { branch: 'feeless/edit-app', url: 'https://github.com/me/app/tree/feeless/edit-app' } }; };
  const el = document.createElement('div'); document.body.appendChild(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { createRoot(el).render(<ProjectWork project={{ full: 'me/app', branch: 'main', paths: ['src/app.js', 'README.md'] }} ask={ask} />); });
  await act(async () => { q('pjw-edit').click(); }); await act(async () => { setVal(q('pjw-find'), 'app'); });
  await act(async () => { q('pjw-hit-src/app.js').click(); }); await act(async () => { jest.advanceTimersByTime(350); }); await act(async () => { await Promise.resolve(); });
  expect(calls.at(-1)).toEqual({ op: 'project_edit', tools: { path: 'src/app.js', dry: true } }); await act(async () => { setVal(q('pjw-text'), 'make a two'); });
  expect(q('pjw-go').textContent).toBe('Rewrite it · ≈$0.0031');
  await act(async () => { q('pjw-go').click(); });
  expect(q('pjw-diff').textContent).toContain('+const a = 2;'); expect(calls.some(c => c.op === 'project_edit_send')).toBe(false);
  await act(async () => { q('pjw-send').click(); });
  expect(calls.at(-1)).toEqual({ op: 'project_edit_send', job: 'd1' }); expect(q('pjw-sent').textContent).toContain('feeless/edit-app'); jest.useRealTimers();
});
