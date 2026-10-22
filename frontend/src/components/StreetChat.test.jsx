import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import StreetChat, { streetParts, xWord, mcWord } from './StreetChat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const FAM = { id: 'c1', tag: 'SIC', name: 'Sicario', color: '#d4af37', badge: { shape: 'heater', c1: '#d4af37', c2: '#7a0f1f', tag: 'SIC' } };
const READ = { room: 'city-fee', reacts: ['🔥', '💀', '🫡', '💰'], hereN: 2, mod: { staff: false, don: true, famId: 'c1' },
  here: [{ address: 'w1', name: 'Don Vito', fam: { ...FAM, don: true } }, { address: 'w2', name: 'lurker', fam: null }],
  vitals: { spark: [0, 2, 5], hour: 7, families: ['SIC'], hot: { symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'kid', fam: 'SIC' } },
  lines: [{ id: 'l1', ts: Date.now() - 60e3, name: 'kid', handle: 'kid', text: '@dev $WIF is cooking', fam: { ...FAM, don: false }, atMe: true,
    calls: [{ symbol: 'WIF', x: 2.4, peakX: 3.1, mcAtCall: 1.2e6, pairAddress: 'P1', chain: 'solana' }], reacts: { '🔥': { n: 3, mine: false } } },
    { id: 'l2', ts: Date.now() - 5e3, name: 'outsider', text: 'gm', fam: { id: 'c9', tag: 'BNK', color: '#ff5fa2', don: false } }] };

test('pure: text parts, x and mcap words', () => {
  expect(streetParts('@dev buy $WIF EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm now').map(p => p.k)).toEqual(['at', 'text', 'tick', 'text', 'ca', 'text']);
  expect(xWord(2.4)).toBe('2.4x'); expect(xWord(0.82)).toBe('-18%'); expect(xWord(12.6)).toBe('13x'); expect(mcWord(1.2e6)).toBe('$1.2M'); expect(mcWord(1.9e9)).toBe('$1.9B');
});

test('the street: crest plates, receipts, @you, block + pulse; react, post and a Don pulls only their own family', async () => {
  const calls = [];
  global.fetch = jest.fn((u, o) => { calls.push([String(u), o]); return Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('/familia/street/fee') && !o ? READ : { ok: true }) }); });
  window.confirm = () => true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StreetChat city="fee" name="FEE CITY" addr="ME" sess="s" />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('city-chat').textContent).toContain('SIC'); expect(q('city-chat').textContent).toContain('ON THE BLOCK');
  expect(q('st-line-l1').className).toContain('is-atme'); expect(q('st-coin').textContent).toContain('2.4x'); expect(q('st-hot').textContent).toContain('$WIF');
  expect(q('st-pull-l1')).not.toBeNull(); expect(q('st-pull-l2')).toBeNull();          // a Don pulls their own family's lines only
  await act(async () => { q('st-react-l1-🔥').click(); });
  expect(q('st-react-l1-🔥').getAttribute('aria-pressed')).toBe('true'); expect(q('st-react-l1-🔥').textContent).toContain('4');
  expect(calls.some(([u, o]) => u.includes('/reactions') && JSON.parse(o.body).emoji === '🔥' && JSON.parse(o.body).voter === 'ME')).toBe(true);
  await act(async () => { q('st-tool-rally').click(); });
  expect(q('st-input').value).toContain('RALLY');
  await act(async () => { q('st-send').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  const post = calls.find(([u, o]) => u.endsWith('/api/reputation/chat') && o?.method === 'POST');
  expect(JSON.parse(post[1].body)).toMatchObject({ room: 'city-fee', address: 'ME', session: 's' });
  await act(async () => { q('st-pull-l1').click(); });
  expect(calls.some(([u, o]) => u.includes('/familia/street/fee/mod') && JSON.parse(o.body).id === 'l1')).toBe(true);
  await act(async () => { root.unmount(); });
});
