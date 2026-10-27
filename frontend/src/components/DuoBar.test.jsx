import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
jest.mock('react-router-dom', () => ({ useLocation: () => ({ pathname: '/familia' }) }), { virtual: true });
import { DuoBar } from './DuoBar';
import { duoPrefs } from '../lib/duo';

const q = id => document.querySelector(`[data-testid="${id}"]`);

test('📱📱 the Duo tab: only on a WIDE Duo in Familia, locked to the edge — ⇄ swaps the halves, saved + on <body>; the dock tab survives a reload', async () => {
  expect(duoPrefs('{"swap":1,"second":"coins"}')).toEqual({ swap: true, second: 'coins' }); expect(duoPrefs('junk')).toEqual({ swap: false, second: 'trade' });   // TRADE is the default dock tab
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DuoBar />); });
  expect(q('duo-bar')).toBeNull();                                            // not a Duo screen
  document.body.classList.add('is-duo'); await act(async () => { window.dispatchEvent(new Event('feeless:duo')); });
  expect(q('duo-bar')).toBeNull();                                            // upright: the halves stack, nothing to swap
  document.body.classList.add('is-duo-land'); await act(async () => { window.dispatchEvent(new Event('feeless:duo')); });
  await act(async () => { q('duo-bar').click(); }); expect(document.body.classList.contains('duo-swap')).toBe(true); expect(q('duo-bar').getAttribute('aria-pressed')).toBe('true');
  expect(JSON.parse(localStorage.getItem('feeless.duo'))).toMatchObject({ swap: true });
  act(() => root.unmount()); document.body.classList.remove('is-duo', 'is-duo-land', 'duo-swap', 'duo-2-trade', 'duo-2-chat', 'duo-2-calls', 'duo-2-coins', 'duo-2-tape');
});
