import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CodeHealth, chRows, editorUrl } from './CodeHealth';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const D = { at: Date.now() / 1000 - 120, root: '/r', counts: { dead_def: 1, dead_export: 2, big: 1 }, totals: { pyLines: 10, jsLines: 5, cssLines: 2 },
  rows: [{ kind: 'dead_def', file: 'backend/a.py', line: 7, name: 'old_fn', fix: 'Nothing calls old_fn() — delete it.' },
    { kind: 'dead_export', file: 'src/x.js', line: 3, name: 'X', how: 'own', fix: 'drop export' },
    { kind: 'dead_export', file: 'src/y.js', line: 4, name: 'Y', how: 'none', fix: 'delete Y' },
    { kind: 'big', file: 'src/z.jsx', line: 1, name: 'Z', lines: 400, fix: 'split' }] };

test('rows filter by kind and by how an export is (un)used', () => {
  expect(chRows(D, 'dead_export', 'none').map(r => r.name)).toEqual(['Y']);
  expect(chRows(D, 'dead_export', 'all')).toHaveLength(2);
  expect(editorUrl('/r', 'backend/a.py', 7)).toBe('vscode://file//r/backend/a.py:7');
});

test('each row opens its file:line and says the fix; tabs switch', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CodeHealth call={() => Promise.resolve(D)} />); });
  const link = [...el.querySelectorAll('a.chl-loc')].find(a => a.textContent.includes('old_fn'));
  expect(link.getAttribute('href')).toBe('vscode://file//r/backend/a.py:7');
  expect(el.textContent).toContain('delete it');
  await act(async () => { el.querySelector('[data-testid=chl-tab-big]').click(); });
  expect(el.textContent).toContain('Z') ; expect(el.querySelector('.chl-bar em').textContent).toBe('400');
});

test('dead files: a row already in the build queue shows queued (titles are cut — match the path start)', () => {
  const { isQueued, chRows } = require('./CodeHealth');
  const r = { file: 'frontend/src/components/SomeVeryLongComponentNameThatGoesOnAndOn/AndHasAnEvenLongerFileName.jsx', name: 'X.jsx', kind: 'dead_file', how: 'none' };
  expect(isQueued([`${r.file.slice(0, 66)}`], r)).toBe(true); expect(isQueued([], r)).toBe(false);
  expect(chRows({ rows: [r, { ...r, how: 'tests', name: 'Y' }] }, 'dead_file', 'none').map(x => x.name)).toEqual(['X.jsx']);
});
