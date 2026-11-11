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

test('💡 SITE-7: the tip card is a stepped tour: TIP n OF total, Next tip retires this one and opens the next, the last one only says Got it', async () => {
  localStorage.removeItem('feeless:tips:n');
  document.body.innerHTML = '<button id="a">A</button><button id="b">B</button>';
  const tips = [['#a', 'Alpha', 'does a'], ['#b', 'Beta', 'does b']];
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FirstTips id="familia" tips={tips} />); });
  const q = s => document.querySelector(`[data-testid="${s}"]`);
  expect(q('tips-familia').className).toContain('is-gold');
  await act(async () => { q('tip-familia-0').click(); });
  expect(document.body.textContent).toContain('TIP 1 OF 2');
  await act(async () => { q('tip-next-familia-0').click(); });
  expect(document.body.textContent).toContain('TIP 2 OF 2'); expect(document.body.textContent).toContain('does b');
  expect(q('tip-next-familia-1')).toBeNull(); expect(q('tips-skip-familia').textContent).toContain('1 tip ');
  localStorage.removeItem('feeless:tips:familia'); await act(async () => root.unmount());
});
