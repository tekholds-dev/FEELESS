import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { tankDots, laneCounts, capX, TANK_LEVELS, LiveTank, bestCoins } from './LiveTank';

test('🫧 the intake lanes: every read lands on its own water level, across = live MC (log $1K…$10M), colour = what it is doing', () => {
  expect(capX(1e3)).toBe(0); expect(capX(1e7)).toBe(1); expect(capX(1e5)).toBeCloseTo(0.5);
  const intake = { coins: [{ mint: 'A', sym: 'A', mc: 5e4, ch: 5, status: 'READY', germ: 4, pair: 'PA' }, { mint: 'B', sym: 'B', mc: 5e5, ch: -5, status: 'CONTENDING', germ: 30 },
    { mint: 'R', sym: 'R', mc: 2e5, ch: 3, status: 'READY', germ: 40 }] };
  const pump = { launches: [{ mint: 'N1', symbol: 'N1', marketCapUsd: 8000, curveProgress: 90 }, { mint: 'N2', symbol: 'N2', marketCapUsd: 4000, curveProgress: 5 }] };
  const trend = { pairs: [{ pairAddress: 'T', baseToken: { address: 'MT', symbol: 'X' }, priceChange: { h1: 40 }, marketCap: 1e6 }] };
  const dots = tankDots({ pump, intake, trend, top: null }); const lane = k => TANK_LEVELS.findIndex(l => l[0] === k);
  const n = laneCounts(dots);
  expect(n[lane('germ')]).toBe(1); expect(n[lane('desk')]).toBe(2); expect(n[lane('new')]).toBe(2); expect(n[lane('trend')]).toBe(1); expect(n[lane('top')]).toBe(0);
  expect(dots.find(d => d.id === 'g-A').tone).toBe('germ');                // at its germ floor — and on NO other row
  expect(dots.filter(d => d.mint === 'A')).toHaveLength(1);
  expect(dots.find(d => d.id === 'd-R').tone).toBe('hot');                 // READY glows gold
  expect(dots.find(d => d.id === 'd-B').tone).toBe('dn');
  expect(dots.find(d => d.id === 'n-N1').tone).toBe('hot');                // about to graduate
  expect(dots.find(d => d.id === 'n-N2').tone).toBe('q');
  expect(dots.find(d => d.id === 'trend-T').pair.pairAddress).toBe('T');   // a tap opens it on the Trenches floor
  expect(tankDots({})).toEqual([]);
});

test('🔎 a tap pops the coin\'s vitals first — TRADE opens it on the Trenches floor (never the war room); a host chart wins', async () => {
  const intake = { coins: [{ mint: 'A', sym: 'AAA', mc: 5e4, ch: 5, status: 'READY', germ: 30, pair: 'PA' }] };
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('intake') ? intake : {}) }));
  const war = []; const onWar = e => war.push(e.detail); window.addEventListener('feeless:war-room', onWar);
  const pops = []; const onPop = () => pops.push(window.location.pathname + window.location.search); window.addEventListener('popstate', onPop);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<LiveTank />); }); await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  await act(async () => { document.querySelector('[data-testid="ltk-dot-d-A"]').click(); });
  expect(pops).toEqual([]);                                                   // nothing opened yet
  const pop = document.querySelector('[data-testid="ltk-pop"]'); expect(pop.textContent).toContain('$AAA'); expect(pop.textContent).toContain('READY');
  await act(async () => { document.querySelector('[data-testid="ltk-trade"]').click(); });
  expect(pops[0]).toBe('/terminal/chat?chain=solana&pair=PA'); expect(war).toEqual([]); expect(document.querySelector('[data-testid="ltk-pop"]')).toBeNull();
  // HQ › Agents hands its own chart in: both buttons land there
  const onChart = jest.fn(); await act(async () => { root.render(<LiveTank onChart={onChart} />); });
  await act(async () => { document.querySelector('[data-testid="ltk-best-1"]').click(); });   // the best strip opens the same vitals
  await act(async () => { document.querySelector('[data-testid="ltk-trade"]').click(); });
  expect(onChart).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'PA' }), 'A'); expect(pops).toHaveLength(1);
  window.removeEventListener('feeless:war-room', onWar); window.removeEventListener('popstate', onPop); act(() => root.unmount());
});

test('🏆 best in the tank: tradable only, no dumps, germ + READY + two feeds agreeing rank first, each coin once', () => {
  const intake = { coins: [{ mint: 'G', sym: 'GERM', mc: 8e4, ch: 2, status: 'CONTENDING', germ: 3, pair: 'PG' }, { mint: 'R', sym: 'RDY', mc: 2e5, ch: 6, status: 'READY', germ: 40, pair: 'PR' },
    { mint: 'D', sym: 'DUMP', mc: 2e5, ch: -25, status: 'READY', pair: 'PD' }, { mint: 'NP', sym: 'NOPOOL', mc: 2e5, ch: 50, status: 'READY' }] };
  const pump = { launches: [{ mint: 'C', symbol: 'CURVE', marketCapUsd: 9e4, curveProgress: 95 }] };
  const trend = { pairs: [{ pairAddress: 'PR', baseToken: { address: 'R', symbol: 'RDY' }, priceChange: { h1: 30 }, marketCap: 2e5, volume: { h1: 5e4 } },
    { pairAddress: 'PV', baseToken: { address: 'V', symbol: 'VOL' }, priceChange: { h1: 3 }, marketCap: 3e5, volume: { h1: 1e3 } }] };
  const best = bestCoins(tankDots({ pump, intake, trend }));
  expect(best.map(b => b.sym)).toEqual(['RDY', 'GERM', 'VOL']);           // no dump, no bare curve, no pool-less coin; RDY = READY + trending
  expect(best[0]).toMatchObject({ rank: 1, why: 'READY', bar: 1 }); expect(best[1].why).toBe('AT GERM'); expect(best[2].why).toBe('VOLUME');
  expect(new Set(best.map(b => b.sym)).size).toBe(best.length); expect(bestCoins([])).toEqual([]);
});

test('ONE row per coin: a coin tagged by many feeds sits on its most specific level only (owner: "same coins on each row")', () => {
  const many = ['open', 'pulse', 'runner', 'list:volume', 'list:movers', 'migr', 'list:ptrend'];
  const C = [{ mint: 'NEW', mc: 5e4, status: 'UNREVIEWED', sources: many, ageMin: 2 }, { mint: 'TOP', mc: 5e4, status: 'UNREVIEWED', sources: many, ageMin: 40 },
    { mint: 'MIG', mc: 5e4, status: 'UNREVIEWED', sources: ['open', 'migr'], ageMin: 300 }, { mint: 'TRD', mc: 5e4, status: 'UNREVIEWED', sources: ['open', 'runner'], ageMin: 300 },
    { mint: 'OLD', mc: 5e4, status: 'UNREVIEWED', sources: ['open'], ageMin: 300 }, { mint: 'TRK', mc: 5e4, status: 'TRACKING', sources: many, ageMin: 2 },
    { mint: 'GRM', mc: 5e4, status: 'CONTENDING', sources: many, ageMin: 2, germ: 2 }].map(c => ({ ...c, sym: c.mint }));
  const dots = tankDots({ intake: { coins: C } });
  expect(dots).toHaveLength(C.length);                                     // never a copy on a second row
  expect(Object.fromEntries(dots.map(d => [d.mint, TANK_LEVELS[d.lane][0]]))).toEqual({ NEW: 'new', TOP: 'top', MIG: 'top', TRD: 'trend', OLD: 'desk', TRK: 'desk', GRM: 'germ' });
  expect(dots.every(d => !d.ready)).toBe(true);
});

test('🎯 N01: ▲ / ▼ step the levels one at a time (its coins as chips), a swipe on the tank moves a row, the name goes back to all', async () => {
  const intake = { coins: [{ mint: 'G', sym: 'GG', mc: 8e4, ch: 2, status: 'CONTENDING', germ: 3, pair: 'PG' }, { mint: 'R', sym: 'RR', mc: 2e5, ch: 6, status: 'READY', germ: 40, pair: 'PR' },
    { mint: 'S', sym: 'SS', mc: 9e5, ch: 1, status: 'CONTENDING', germ: 50, pair: 'PS' }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(intake) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<LiveTank />); }); await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  const $ = id => document.querySelector(`[data-testid="${id}"]`);
  expect($('ltk-row-name').textContent).toContain('ALL LEVELS'); expect($('live-tank').className).not.toContain('is-row');
  await act(async () => { $('ltk-down').click(); });
  expect($('ltk-row-name').textContent).toContain('GERM'); expect($('ltk-up').disabled).toBe(true); expect($('ltk-chip-g-G')).not.toBeNull();
  expect($('ltk-dot-g-G').className).toContain('is-row'); expect($('ltk-dot-d-R').className).not.toContain('is-row');
  await act(async () => { $('ltk-down').click(); });
  expect($('ltk-row-name').textContent).toContain('DESK'); expect([...document.querySelectorAll('[data-testid^="ltk-chip-"]')].map(b => b.dataset.testid)).toEqual(['ltk-chip-d-S', 'ltk-chip-d-R']);   // biggest MC first
  await act(async () => { $('ltk-chip-d-R').click(); }); expect($('ltk-pop').textContent).toContain('$RR');
  const touch = (type, y) => { const e = new Event(type, { bubbles: true }); const t = [{ clientX: 100, clientY: y }]; Object.defineProperty(e, type === 'touchend' ? 'changedTouches' : 'touches', { value: t }); return e; };
  await act(async () => { $('ltk-field').dispatchEvent(touch('touchstart', 200)); $('ltk-field').dispatchEvent(touch('touchend', 120)); });   // swipe up → a row down
  expect($('ltk-row-name').textContent).toContain('TOP NEW');
  await act(async () => { $('ltk-field').dispatchEvent(touch('touchstart', 100)); $('ltk-field').dispatchEvent(touch('touchend', 180)); });   // swipe down → a row up
  expect($('ltk-row-name').textContent).toContain('DESK');
  await act(async () => { $('ltk-row-name').click(); }); expect($('ltk-row-name').textContent).toContain('ALL LEVELS');
  act(() => root.unmount()); el.remove();
});
