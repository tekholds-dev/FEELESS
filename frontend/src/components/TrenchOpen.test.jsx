import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('open gates: every front-runner with its safety mark; callouts feed with each kind\'s record; tap opens the coin', async () => {
  const rows = Array.from({ length: 12 }, (_, i) => ({ mint: `M${i}`, pairAddress: `P${i}`, symbol: `C${i}`, rank: i + 1, front: 90 - i, vol1h: 150000 - i * 9000, txns1h: 400, buyShare: 61, mcap: 80000, ageH: 0.4,
    chg5m: i === 1 ? -4 : 6, safe: i === 0 ? true : i === 1 ? false : null, fails: i === 1 ? ['top-10 < 20%'] : i ? ['not scanned yet — holders unknown'] : [], call: i === 0 ? 'leader' : null }));
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ rows, seen: 140, everySec: 210,
    kinds: [{ key: 'leader', icon: '🔥', name: 'Volume leader', rule: 'top 5', proof: { n: 9, medPct: -12, wonPct: 33 } }, { key: 'mover', icon: '🚀', name: 'Mover', rule: 'r', proof: { n: 2 } }, { key: 'fresh', icon: '🆕', name: 'Fresh launch', rule: 'r', proof: { n: 0 } }],
    feed: [{ kind: 'leader', mint: 'M0', symbol: 'C0', pairAddress: 'P0', mins: 5, pct: 30, live: true, at: 2 }, { kind: 'fresh', mint: 'MZ', symbol: 'ZED', mins: 125, pct: -100, live: false, at: 1 }] }) }));
  const { TrenchOpen } = require('./TrenchOpen'); const { openCoin } = require('./CoinDrawer');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TrenchOpen max={10} />); }); await tick(30);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('trench-open').textContent).toContain('12 of 140 coins');
  expect(el.querySelectorAll('.top-tr:not(.top-th)').length).toBe(10);
  expect(q('open-C0').className).toContain('is-safe'); expect(q('open-C0').textContent).toContain('✅ safe'); expect(q('open-C0').textContent).toContain('🔥'); expect(q('open-C0').textContent).toContain('$C0'); expect(q('open-C0').textContent).toContain('24m');
  expect(q('open-C1').className).toContain('is-bad'); expect(q('open-C1').querySelector('.top-safe').getAttribute('data-tip')).toContain('Did not pass: top-10 < 20%');
  expect(q('open-C2').className).toContain('is-unk'); expect(q('open-C2').textContent).toContain('❔ unscanned');
  await act(async () => { q('open-more').click(); }); expect(el.querySelectorAll('.top-tr:not(.top-th)').length).toBe(12);
  expect(q('trench-open').textContent).toContain('EVERY 3.5 MIN');
  expect(q('call-kind-leader').textContent).toContain('-12%'); expect(q('call-kind-leader').textContent).toContain('33% up'); expect(q('call-kind-mover').textContent).toContain('2 of 5 settled');
  const feed = q('call-feed').textContent; for (const x of ['$C0', 'volume leader · called 5m ago', '+30%', 'since the call', '$ZED', 'fresh launch · called 2h ago', '-100%', 'after 1h']) expect(feed).toContain(x);
  await act(async () => { q('open-view-C0').click(); }); expect(openCoin).toHaveBeenCalledWith({ mint: 'M0', pairAddress: 'P0', symbol: 'C0' });
  // inside the swap picker every row has a Pick button that hands the coin to the picker
  const picked = jest.fn(); await act(async () => { root.render(<TrenchOpen max={10} onPick={picked} />); }); await tick(30);
  expect(q('open-view-C0')).toBeNull(); await act(async () => { q('open-pick-C1').click(); }); expect(picked).toHaveBeenCalledWith(expect.objectContaining({ mint: 'M1', symbol: 'C1' }));
  await act(async () => { root.unmount(); });
});
