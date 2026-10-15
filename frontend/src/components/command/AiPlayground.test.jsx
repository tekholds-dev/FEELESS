import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AiPlayground } from './AiPlayground';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
test('the code lab shows a proposal with line numbers and files it to the build queue on approve', async () => {
  const item = { id: 'c1', title: 'hold one more read', file: 'backend/office.py', kind: 'change', why: 'exits too fast', risk: 'holds a loser', code: 'def f():\n    return 1', diff: '--- a\n+++ b\n-    return 0\n+    return 1', changed: ['f'], new: [], status: 'proposed', target: 'reaper', by: 'DESKTOP AI' };
  const call = jest.fn((path, opts) => Promise.resolve(path.endsWith('/decide') ? { item: { ...item, status: 'approved', build: 'b9' }, items: [{ ...item, status: 'approved', build: 'b9' }] }
    : { items: [item], targets: [['reaper', '☠ Reaper — exits', 'backend/office.py']] }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AiPlayground call={call} />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('apg-diff').querySelector('.is-add').textContent).toContain('return 1'); expect(q('apg-diff').querySelector('.is-del')).toBeTruthy();   // the preview first
  await act(async () => { q('apg-v-code').click(); });
  expect(q('apg-code').textContent).toContain('1def f():'); expect(q('apg-t-reaper')).toBeTruthy();
  await act(async () => { q('apg-approve').click(); });
  await act(async () => { await Promise.resolve(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/playground/decide', expect.objectContaining({ method: 'POST' }));
  expect(q('apg-prop').className).toContain('is-approved');
});


test('items left by the old HTML playground never crash the code lab', () => {
  const { codeOnly } = require('./AiPlayground');
  expect(codeOnly([{ id: 'p1', prompt: 'neon', html: '<html></html>' }, { id: 'c1', code: 'def f(): pass' }])).toEqual([{ id: 'c1', code: 'def f(): pass', status: 'proposed', title: 'code change', file: '' }]);
});
