import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn(), addToCard: jest.fn() }));
jest.mock('./terminal/PriceChart', () => ({ PriceChart: ({ interval }) => <div data-testid="pc">{interval}</div> }));
jest.mock('./WarRoomHost', () => ({ openWarRoom: jest.fn() }));
jest.mock('./MiniChart', () => ({ openMiniChart: jest.fn() }));
jest.mock('../lib/candles', () => ({ prefetchAllIntervals: jest.fn(), prefetchInterval: jest.fn() }));
beforeEach(() => { try { localStorage.clear(); } catch { /* none */ } });
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
  expect(q('open-split')).not.toBeNull();   // ⚡ split is the default; ≡ List = the OG table
  await act(async () => { q('open-l-list').click(); }); expect(q('open-split')).toBeNull(); expect(localStorage.getItem('feeless.openLayout')).toBe('list');
  expect(el.querySelectorAll('.top-tr:not(.top-th)').length).toBe(10);
  expect(q('open-C0').className).toContain('is-safe'); expect(q('open-C0').textContent).toContain('✅ safe'); expect(q('open-C0').textContent).toContain('🔥'); expect(q('open-C0').textContent).toContain('$C0'); expect(q('open-C0').textContent).toContain('24m');
  expect(q('open-C1').className).toContain('is-bad'); expect(q('open-C1').querySelector('.top-safe').getAttribute('data-tip')).toContain('Did not pass: top-10 < 20%');
  expect(q('open-C2').className).toContain('is-unk'); expect(q('open-C2').textContent).toContain('❔ unscanned');
  await act(async () => { q('open-more').click(); }); expect(el.querySelectorAll('.top-tr:not(.top-th)').length).toBe(12);
  expect(q('trench-open').textContent).toContain('EVERY 3.5 MIN');
  expect(q('call-kind-leader').textContent).toContain('-12%'); expect(q('call-kind-leader').textContent).toContain('33% up'); expect(q('call-kind-mover').textContent).toContain('2 of 5 settled');
  const feed = q('call-feed').textContent; for (const x of ['$C0', 'volume leader · called 5m ago', '+30%', 'since the call', '$ZED', 'fresh launch · called 2h ago', '-100%', 'after 1h']) expect(feed).toContain(x);
  await act(async () => { q('open-view-C0').click(); }); expect(document.querySelector('[data-testid="trench-quick"]').textContent).toContain('$C0');   // ⚡ quick look, not the side drawer
  expect(openCoin).not.toHaveBeenCalled(); await act(async () => { document.querySelector('.tql-x').click(); }); expect(document.querySelector('[data-testid="trench-quick"]')).toBeNull();
  await act(async () => { q('call-feed').querySelectorAll('button')[1].click(); }); expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'MZ' }));   // a callout coin no longer on the list still opens the drawer
  // inside the swap picker every row has a Pick button that hands the coin to the picker
  const picked = jest.fn(); await act(async () => { root.render(<TrenchOpen max={10} onPick={picked} />); }); await tick(30);
  expect(q('open-view-C0')).toBeNull(); await act(async () => { q('open-pick-C1').click(); }); expect(picked).toHaveBeenCalledWith(expect.objectContaining({ mint: 'M1', symbol: 'C1' }));
  await act(async () => { root.unmount(); });
});

test('split view: newest column youngest first (🧹 clean hides failed scans + busted reads), hot lane = what would rush (busted BOND RUN → avoid), quick look shows every vital + picks', async () => {
  const tv = (word, tone, kind = 'trench', m = 70) => ({ kind, call: ['•', word, tone], meters: [['A', m], ['B', 20]], tags: [] });
  const rows = [
    { mint: 'A', pairAddress: 'PA', symbol: 'OLD', ageH: 5, mcap: 1e5, tv: tv('SEND IT', 'good'), safe: true, top10: 18, dev: 1, buyShare: 64, vol1h: 60000, vol5m: 9000, txns1h: 800 },
    { mint: 'B', pairAddress: 'PB', symbol: 'BABY', ageH: 0.05, mcap: 9000, tv: tv('NEAR BOND', 'good', 'curve', 91), curvePct: 91, safe: null },
    { mint: 'C', pairAddress: 'PC', symbol: 'RUN', ageH: 1, mcap: 3e4, tv: tv('BOND RUN', 'good', 'curve', 80), curvePct: 80, safe: true, insiders: 12 },
    { mint: 'D', pairAddress: 'PD', symbol: 'RUG', ageH: 0.5, mcap: 2e4, tv: tv('RUG BAIT', 'bad'), safe: false, fails: ['top-10'] },
    { mint: 'E', pairAddress: 'PE', symbol: 'MEH', ageH: 3, mcap: 2e4, tv: tv('WATCH', 'warn'), safe: null }];
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ rows, seen: 5, kinds: [], feed: [] }) }));
  const { TrenchOpen } = require('./TrenchOpen');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const picked = jest.fn();
  await act(async () => { root.render(<TrenchOpen max={10} onPick={picked} />); }); await tick(30);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  const syms = col => [...q(col).querySelectorAll('.tsp-card')].map(x => x.getAttribute('data-testid'));
  expect(syms('split-new')).toEqual(['rc-BABY', 'rc-MEH', 'rc-OLD']);              // 🧹 clean: the failed scan and the busted BOND RUN are hidden
  expect(q('split-clean').textContent).toContain('2 hidden');
  await act(async () => { q('split-clean').click(); }); expect(syms('split-new')).toEqual(['rc-BABY', 'rc-RUG', 'rc-RUN', 'rc-MEH', 'rc-OLD']);
  expect(syms('split-reads')).toEqual(['rc-OLD', 'rc-BABY']);   // 🔥 hot lane: what the rush board would take, best rush first
  expect(q('split-reads').textContent).toContain('NEAR BOND · 1'); expect(q('lane-avoid').textContent).toContain('2');
  expect(q('split-reads').querySelector('[data-testid="rush-pick-OLD"]')).not.toBeNull();   // ⚡ one tap, right on the card
  expect(q('split-new').querySelector('[data-testid="rc-BABY"]').textContent).toContain('🔔 91%');
  await act(async () => { q('lane-avoid').click(); }); expect(syms('split-reads')).toEqual(['rc-RUN', 'rc-RUG']);   // BOND RUN reads −84%/1h: avoid
  await act(async () => { q('split-new').querySelector('[data-testid="rc-OLD"]').click(); }); await tick(30);
  const ql = () => document.querySelector('[data-testid="trench-quick"]');
  expect(ql().textContent).toContain('$OLD'); expect(ql().querySelector('[data-testid="tql-vitals"]').textContent).toContain('TOP 10'); expect(ql().textContent).toContain('18%');
  expect(ql().querySelector('[data-testid="pc"]')).not.toBeNull();   // the live chart is in the panel
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' })); }); expect(ql().textContent).toContain('$MEH');   // ← → walk the same list
  await act(async () => { ql().querySelector('[data-testid="tql-pick"]').click(); }); expect(picked).toHaveBeenCalledWith(expect.objectContaining({ mint: 'E' })); expect(ql()).toBeNull();
  await act(async () => { root.unmount(); });
});
