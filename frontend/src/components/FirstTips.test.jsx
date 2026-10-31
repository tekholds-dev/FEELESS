import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FirstTips } from './FirstTips';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('💡 first-time tips: a spot per control, one line on hover, Got it retires one, Skip all retires the page — and they never come back', async () => {
  localStorage.removeItem('feeless:tips:t');
  document.body.innerHTML = '<button id="a">A</button><button id="b">B</button>';
  Element.prototype.getBoundingClientRect = function () { return { top: 50, right: 120, bottom: 80, width: 100, height: 30, left: 20 }; };
  global.requestAnimationFrame = cb => { cb(); return 1; }; global.cancelAnimationFrame = () => {};
  const tips = [['#a', 'Alpha', 'does a'], ['#b', 'Beta', 'does b']];
  const el = document.createElement('div'); document.body.appendChild(el); let root = createRoot(el);
  await act(async () => { root.render(<FirstTips id="t" tips={tips} />); });
  const q = s => document.querySelector(`[data-testid="${s}"]`);
  expect(q('tip-t-0')).not.toBeNull(); expect(q('tips-skip-t').textContent).toContain('2 tips');
  await act(async () => { q('tip-t-0').click(); });
  expect(document.body.textContent).toContain('does a');
  await act(async () => { q('tip-ok-t-0').click(); });
  expect(q('tip-t-0')).toBeNull(); expect(JSON.parse(localStorage.getItem('feeless:tips:t'))).toEqual([0]);
  await act(async () => { q('tips-skip-t').click(); });
  expect(q('tips-t')).toBeNull();
  await act(async () => root.unmount()); root = createRoot(el);
  await act(async () => { root.render(<FirstTips id="t" tips={tips} />); });
  expect(q('tips-t')).toBeNull();   // first time only
  await act(async () => root.unmount());
});
