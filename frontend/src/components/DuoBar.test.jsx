import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
jest.mock('react-router-dom', () => ({ useLocation: () => ({ pathname: '/terminal/chat' }) }), { virtual: true });
import { DuoBar } from './DuoBar';
import { duoPrefs } from '../lib/duo';

const q = id => document.querySelector(`[data-testid="${id}"]`);

test('📱📱 the Duo bar: hidden off a Duo, folds to a small button, ⇄ swaps the screens, the Trenches pick CHAT | CALLS — saved + on <body>', async () => {
  expect(duoPrefs('{"swap":1,"second":"calls"}')).toEqual({ swap: true, second: 'calls' }); expect(duoPrefs('junk')).toEqual({ swap: false, second: 'trade' });   // TRADE beside the chart is the default
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DuoBar />); });
  expect(q('duo-fab')).toBeNull();                                            // not a Duo screen
  document.body.classList.add('is-duo'); await act(async () => { window.dispatchEvent(new Event('feeless:duo')); });
  await act(async () => { q('duo-fab').click(); });
  await act(async () => { q('duo-swap').click(); }); expect(document.body.classList.contains('duo-swap')).toBe(true);
  await act(async () => { q('duo-2-calls').click(); }); expect(document.body.classList.contains('duo-2-calls')).toBe(true); expect(document.body.classList.contains('duo-2-trade')).toBe(false);
  expect(JSON.parse(localStorage.getItem('feeless.duo'))).toEqual({ swap: true, second: 'calls' });
  act(() => root.unmount()); document.body.classList.remove('is-duo', 'duo-swap', 'duo-2-calls', 'duo-2-trade', 'duo-2-chat');
});
