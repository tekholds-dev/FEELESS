import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { AssetShelf } from './AssetShelf';

const FOUND = [{ id: 'cm-1', name: 'Neon.jpg', kind: 'image', thumb: 't.jpg', url: 'https://upload.wikimedia.org/a/Neon.jpg', lic: 'CC BY-SA 4.0', by: 'Ann', src: 'Wikimedia Commons' }];
const ROW = { id: 'abc123def456', name: 'Neon.jpg', kind: 'image', size: 2000, lic: 'CC BY-SA 4.0', by: 'Ann' };

test('🗂 the shelf finds real media with its licence, keeps one to My files, and hands it to the studio', async () => {
  const calls = []; let mine = { rows: [], used: 0, max: 250e6 };
  const work = jest.fn(async (_c, b) => { calls.push(b);
    if (b.op === 'assets_list') return mine; if (b.op === 'assets_find') return { rows: FOUND, q: 'neon' };
    if (b.op === 'assets_keep') { mine = { rows: [ROW], used: 2000, max: 250e6 }; return { row: ROW, ...mine }; } return mine; });
  const onUse = jest.fn(async () => {});
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AssetShelf cat={{ id: 'c1' }} work={work} kinds={['image', 'audio']} onUse={onUse} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(calls.find(c => c.op === 'assets_find').job).toBe('image');
  expect(q('asf-grid').textContent).toMatch(/CC BY-SA 4\.0 · Ann/);
  await act(async () => { q('asf-use').click(); });
  expect(calls.find(c => c.op === 'assets_keep').tools.url).toBe(FOUND[0].url);
  expect(onUse).toHaveBeenCalledWith(ROW, expect.stringContaining('/api/cats/c1/asset/abc123def456'));
  await act(async () => { q('asf-mine').click(); });
  expect(q('asf-dl').getAttribute('href')).toMatch(/dl=1/);
  await act(async () => { q('asf-kind-audio').click(); });
  expect(el.textContent).toMatch(/No sound in My files yet/);
  await act(async () => { root.unmount(); });
});
