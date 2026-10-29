import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { tankDots, laneCounts, capX, TANK_LEVELS, LiveTank, bestCoins } from './LiveTank';

test('🫧 the intake lanes: every read lands on its own water level, across = live MC (log $1K…$10M), colour = what it is doing', () => {
  expect(capX(1e3)).toBe(0); expect(capX(1e7)).toBe(1); expect(capX(1e5)).toBeCloseTo(0.5);
  const intake = { coins: [{ mint: 'A', sym: 'A', mc: 5e4, ch: 5, status: 'READY', germ: 4, pair: 'PA' }, { mint: 'B', sym: 'B', mc: 5e5, ch: -5, status: 'CONTENDING', germ: 30 }] };
  const pump = { launches: [{ mint: 'N1', symbol: 'N1', marketCapUsd: 8000, curveProgress: 90 }, { mint: 'N2', symbol: 'N2', marketCapUsd: 4000, curveProgress: 5 }] };
  const trend = { pairs: [{ pairAddress: 'T', baseToken: { address: 'MT', symbol: 'X' }, priceChange: { h1: 40 }, marketCap: 1e6 }] };
  const dots = tankDots({ pump, intake, trend, top: null }); const lane = k => TANK_LEVELS.findIndex(l => l[0] === k);
  const n = laneCounts(dots);
  expect(n[lane('germ')]).toBe(1); expect(n[lane('desk')]).toBe(2); expect(n[lane('new')]).toBe(2); expect(n[lane('trend')]).toBe(1); expect(n[lane('top')]).toBe(0);
  expect(dots.find(d => d.id === 'g-A').tone).toBe('germ');                // at its germ floor
  expect(dots.find(d => d.id === 'd-A').tone).toBe('hot');                 // READY glows gold
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

test('shared discovery supplies source lanes without separate feed responses', () => {
  const dots = tankDots({ intake: { coins: [{ mint: 'RAW', sym: 'RAW', mc: 50000, status: 'UNREVIEWED', sources: ['open', 'pulse'], ageMin: 2 }] } });
  expect(dots.some(d => TANK_LEVELS[d.lane][0] === 'new')).toBe(true);
  expect(dots.some(d => TANK_LEVELS[d.lane][0] === 'desk')).toBe(true);
  expect(dots.every(d => !d.ready)).toBe(true);
});
