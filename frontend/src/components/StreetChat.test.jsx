import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import StreetChat, { streetParts, xWord, mcWord, trailPath } from './StreetChat';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const FAM = { id: 'c1', tag: 'SIC', name: 'Sicario', color: '#d4af37', badge: { shape: 'heater', c1: '#d4af37', c2: '#7a0f1f', tag: 'SIC' } };
const READ = { room: 'city-fee', reacts: ['🔥', '💀', '🫡', '💰'], hereN: 2, mod: { staff: false, don: true, famId: 'c1' },
  here: [{ address: 'w1', name: 'Don Vito', fam: { ...FAM, don: true } }, { address: 'w2', name: 'lurker', fam: null }],
  vitals: { spark: [0, 2, 5], hour: 7, families: ['SIC'], hot: { symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'kid', fam: 'SIC' }, heat: 3 },
  hits: [{ symbol: 'WIF', peakX: 3.1, x: 2.4, by: 'kid', ago: 600, pairAddress: 'P1', chain: 'solana', fam: { tag: 'SIC', color: '#d4af37' } },
    { symbol: 'BONK', peakX: 2, x: 1.4, by: 'vito', ago: 60, pairAddress: 'P2', chain: 'solana', fam: null }, { symbol: 'POPCAT', peakX: 1.6, x: 1.1, by: 'x', ago: 9, pairAddress: 'P3' }],
  slow: { sec: 30, by: '[SIC] Vito', left: 1500, wait: 0 }, slowChoices: [0, 10, 30, 60], typing: ['kid', 'pinky'],
  lines: [{ id: 'l1', ts: Date.now() - 60e3, name: 'kid', handle: 'kid', text: '@dev $WIF is cooking', fam: { ...FAM, don: false }, atMe: true,
    calls: [{ symbol: 'WIF', x: 2.4, peakX: 3.1, mcAtCall: 1.2e6, pairAddress: 'P1', chain: 'solana', trail: [[1000, 1], [1300, 2.2], [1600, 3.1], [1900, 2.6]] }], reacts: { '🔥': { n: 3, mine: false } } },
    { id: 'l2', ts: Date.now() - 5e3, name: 'outsider', text: 'gm', fam: { id: 'c9', tag: 'BNK', color: '#ff5fa2', don: false } },
    { id: 'l3', ts: Date.now() - 3e3, name: 'pinky', text: 'WIF still cooking?', parentId: 'l1', fam: null }] };

test('pure: text parts, x and mcap words', () => {
  expect(streetParts('@dev buy $WIF EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm now').map(p => p.k)).toEqual(['at', 'text', 'tick', 'text', 'ca', 'text']);
  const g = trailPath([[0, 1], [300, 4], [600, 2]]);
  expect(g.base).toBeGreaterThan(g.peak[1]); expect(g.peak[0]).toBeCloseTo(29); expect(g.d.startsWith('M0.0 ')).toBe(true); expect(trailPath([[0, 1]])).toBeNull();
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
  expect(q('st-trail')).not.toBeNull();                                                 // the receipt draws its run since the call
  expect(q('st-tape').textContent).toContain('$BONK'); expect(el.querySelectorAll('.st-hit[aria-hidden]').length).toBe(3);   // the hits tape rolls (a duplicate run)
  expect(q('city-chat').className).toContain('is-heat-3'); expect(q('st-heat').textContent).toContain('ON FIRE'); expect(el.querySelector('.st-flash')).not.toBeNull();
  expect(q('st-slow').textContent).toContain('30s');
  expect(q('st-typing').textContent).toContain('kid, pinky typing');                     // ✍ who is typing
  expect(q('st-line-l3').textContent).toContain('↩ kid');                                  // a reply names its line
  await act(async () => { q('st-thread-l1').click(); });
  expect(q('st-thread-list-l1').textContent).toContain('WIF still cooking?');              // 💬 the call's own thread
  await act(async () => { const inp = q('st-input'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(inp, 'gm'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(calls.some(([u, o]) => u.includes('/familia/street/fee/typing') && JSON.parse(o.body).session === 's')).toBe(true);
  await act(async () => { q('st-tool-slow').click(); });
  await act(async () => { q('st-slow-10').click(); });
  expect(calls.some(([u, o]) => u.includes('/familia/street/fee/mod') && JSON.parse(o.body).act === 'slow' && JSON.parse(o.body).sec === 10)).toBe(true);
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

test('🏆 the best call strip picks the 24h best call (≥ 1.2x) and Pump\'s hottest liquid coin', () => {
  const { bestCall, pumpHot } = require('./StreetChat'); const now = 1_800_000_000;
  const calls = [{ pairAddress: 'A', symbol: 'OLD', peakX: 40, at: now - 90000 }, { pairAddress: 'B', symbol: 'MID', peakX: 3.1, at: now - 600 }, { pairAddress: 'C', symbol: 'TOP', peakX: 6.4, at: now - 3600 }, { pairAddress: 'D', symbol: 'FLAT', peakX: 1.05, at: now - 60 }];
  expect(bestCall(calls, now).symbol).toBe('TOP'); expect(bestCall([calls[3]], now)).toBeNull(); expect(bestCall(null, now)).toBeNull();
  const pairs = [{ baseToken: { address: 'x', symbol: 'THIN' }, liquidity: { usd: 900 }, priceChange: { m5: 300 } }, { baseToken: { address: 'y', symbol: 'HOT' }, liquidity: { usd: 40000 }, priceChange: { m5: 38 } },
    { baseToken: { address: 'z', symbol: 'DOWN' }, liquidity: { usd: 90000 }, priceChange: { m5: -5 } }];
  expect(pumpHot(pairs).baseToken.symbol).toBe('HOT'); expect(pumpHot([pairs[2]])).toBeNull();
});
