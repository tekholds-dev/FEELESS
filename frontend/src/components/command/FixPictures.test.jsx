import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { FixFolder } from './OwnerFolders';

const IMG = 'data:image/jpeg;base64,AAAA';
test('📸 a fix waiting for review shows BEFORE (running site) beside AFTER (its branch), big on click, and can retake them', async () => {
  const posts = [];
  const call = jest.fn(async (path, opts) => {
    if (opts?.method === 'POST') { posts.push(JSON.parse(opts.body)); return { ok: true }; }
    if (path.startsWith('/admin/fix/pictures/')) return { before: IMG, after: IMG };
    return { busy: null, seats: [{ key: 'cloud', name: 'Cloud mind', free: false }], cases: [{ id: 'pick-is-not-defined', text: '[panel crash] This page: pick is not defined', page: '/terminal', times: 2,
      run: { stage: 'review', by: 'Cloud mind', cause: 'pick was renamed', branch: 'fix/pick-1', before: 'pick-is-not-defined-before.jpg', after: 'pick-is-not-defined-after.jpg', checks: [{ name: 'Tests near this file', ok: true }], at: 5 } },
    { id: 'other', text: '[auto crash] x', page: '/', times: 1, run: { stage: 'review', branch: 'fix/o', beforeWhy: '', afterWhy: 'The machine was busy, so the after picture waits. Take it again later.', at: 6 } }] };
  });
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(<FixFolder call={call} />)); await act(async () => {});
  const q = id => box.querySelector(`[data-testid="${id}"]`);
  expect(q('fix-pic-before-pick-is-not-defined').querySelector('img').getAttribute('src')).toBe(IMG);
  expect(q('fix-pic-after-pick-is-not-defined').textContent).toContain('fix/pick-1');
  expect(q('fix-pic-after-other').textContent).toContain('The machine was busy');
  await act(async () => { q('fix-pic-after-pick-is-not-defined').querySelector('button').click(); }); expect(q('fix-pic-big')).not.toBeNull();
  await act(async () => { q('fix-pic-big').click(); }); expect(q('fix-pic-big')).toBeNull();
  await act(async () => { q('fix-pics-again-pick-is-not-defined').click(); }); expect(posts.at(-1)).toEqual({ id: 'pick-is-not-defined', pictures: true });
  act(() => root.unmount());
});
