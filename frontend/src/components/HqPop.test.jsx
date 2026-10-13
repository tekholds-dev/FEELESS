import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import HqPop, { hqMood, HQ_JUMPS } from './HqPop';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: global.__wallet, signMessage: async () => 'sig' }) }));
jest.mock('./command/HqDeck', () => { const R = require('react'); return { HqDeck: ({ address, startTab }) => R.createElement('div', { 'data-testid': 'hq-shell' }, `HQ for ${address} on ${startTab}`) }; });
const q = id => document.querySelector(`[data-testid="${id}"]`);
const answer = who => { global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(who) })); };
const tick = async (n = 6) => { for (let i = 0; i < n; i += 1) await act(async () => { await new Promise(r => setTimeout(r, 0)); }); };   // eslint-disable-line no-await-in-loop
const mount = async () => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(<HqPop />); }); await tick(); return { el, root }; };
beforeEach(() => { document.body.innerHTML = ''; sessionStorage.clear(); global.__wallet = { address: 'CREATOR', chain: 'solana' }; });

test('⚡ only the creator wallet gets the HQ button; one click opens the whole HQ, Esc closes it', async () => {
  answer({ isAdmin: true, isOwner: true });
  await mount();
  expect(global.fetch.mock.calls[0][0]).toContain('/api/reputation/admin/whoami?address=CREATOR');
  expect(q('hq-pop-open')).not.toBeNull(); expect(q('hq-pop')).toBeNull();            // no HQ on the page until the click
  await act(async () => { q('hq-pop-open').click(); }); await tick();
  expect(q('hq-shell').textContent).toBe('HQ for CREATOR on agents');
  expect(q('hq-pop-mood').getAttribute('data-mood')).toBe('idle');
  const got = []; const on = e => got.push(e.detail); window.addEventListener('feeless:hq-go', on);
  await act(async () => { q('hq-pop-go-wallet').click(); });
  expect(got).toEqual([{ tab: 'fuse', panel: 'wallet' }]); expect(q('hq-pop-go-wallet').className).toContain('active');
  window.removeEventListener('feeless:hq-go', on);
  expect(document.body.classList.contains('hqp-open')).toBe(true);
  await act(async () => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); });
  expect(q('hq-pop')).toBeNull(); expect(document.body.classList.contains('hqp-open')).toBe(false);
});

test('an admin who is not the creator, and a visitor, get nothing at all', async () => {
  global.__wallet = { address: 'MOD', chain: 'solana' }; answer({ isAdmin: true, isOwner: false });
  const { el } = await mount();
  expect(global.fetch).toHaveBeenCalled(); expect(el.innerHTML).toBe(''); expect(q('hq-pop-open')).toBeNull();
  global.__wallet = null; answer({ isAdmin: false, isOwner: false });
  const v = await mount(); expect(v.el.innerHTML).toBe('');
});

test('the header says what HQ is really doing', () => {
  expect(hqMood({ n: 0 })).toMatchObject({ key: 'idle', word: 'LOCKED IN' });
  expect(hqMood({ n: 1, label: '💵 Top up' })).toMatchObject({ key: 'work', word: 'SENDING IT', line: '💵 Top up' });
  expect(hqMood({ n: 2, slow: true, label: 'Top up' }).key).toBe('slow');
  expect(HQ_JUMPS.map(j => j[0])).toEqual(['agents', 'wallet', 'fuse', 'money', 'lag', 'fees']);
});
